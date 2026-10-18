"""Baseline P50/P90 from the PVGIS TMY (docs/02 §3.3). Frozen once approved (DB trigger, invariant 1).

Same model chain and loss register as expected output, so weather is the only difference to E_bl_aw:
    P50_month = Σ_TMY-month E_potential_dp × (1 − a_soiling − a_availability − a_curtailment − a_grid)
    P90 = P50 × (1 − z_p90 × σ_total)
TMY rows are re-stamped onto the contract year. D21: PVGIS components close (DNI·cos z + DHI = GHI) at the hh:00 UTC
stamp itself, so the stamp is the evaluation instant: the hour runs stamp − 30 min … stamp + 30 min. Feb 29
repeats Feb 28.
"""

import calendar
from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import Connection, text

from app.core.bulk import copy_frame, stable_uuid
from app.core.money import quantize_inr
from app.core.timeutil import PLANT_TZ
from app.finance.cfads import split_annual
from app.performance import model


class BaselineError(ValueError):
    pass


def restamp(tmy: pd.DataFrame, year: int) -> pd.DataFrame:
    t = tmy.copy()
    t.index = pd.DatetimeIndex([ts.replace(year=year) for ts in t.index])
    t = t.sort_index()
    if calendar.isleap(year):
        feb28 = t[(t.index.month == 2) & (t.index.day == 28)].copy()
        feb28.index = feb28.index + pd.Timedelta(days=1)
        t = pd.concat([t, feb28]).sort_index()
    return t


def monthly_p50(tmy: pd.DataFrame, plant: dict, year: int) -> pd.DataFrame:
    p = model.ChainParams.from_plant(plant)
    w = restamp(tmy, year)
    w.index = w.index - pd.Timedelta(minutes=30)  # interval start; the chain evaluates at start + 30 min = stamp
    r = model.run_chain(w, p, 1.0)
    n_inv = plant["inverter"]["count"]
    dp = r["e_potential_kwh"] * n_inv * (1 - p.export_loss)
    local = r.index.tz_convert(PLANT_TZ)
    in_year = local.year == year
    month = local.to_period("M").to_timestamp().date
    ep = dp[in_year].groupby(month[in_year]).sum()
    assumed = plant["loss_register"]["attributable_assumed"]
    factor = 1 - sum(float(assumed[k]) for k in ("soiling", "availability", "curtailment", "grid_unavailability"))
    return pd.DataFrame({"ep_dp_kwh": ep, "p50_kwh": ep * factor})


def build_rows(
    tmy: pd.DataFrame,
    tmy_inputs: dict,
    plant: dict,
    cfg: dict,
    loan_debt_annual: Decimal,
    version: int,
    supersedes: int | None,
) -> tuple[list[dict], dict]:
    year = pd.Timestamp(cfg["period"]["start"]).year
    m = monthly_p50(tmy, plant, year)
    annual = float(m["p50_kwh"].sum())
    lo, hi = cfg["energy_kwh"]["sanity_range_annual"]
    if not lo <= annual <= hi:
        raise BaselineError(
            f"annual P50 {annual:,.0f} kWh outside sanity range [{lo:,}, {hi:,}]: "
            "check azimuth convention, units, timezone shift"
        )
    unc = cfg["uncertainty"]
    p90_factor = Decimal("1") - Decimal(str(unc["z_p90"])) * Decimal(str(unc["sigma_total"]))
    fin = cfg["finance"]
    tariff = Decimal(fin["tariff_inr_per_kwh"])
    opex = split_annual(Decimal(fin["opex_inr_annual"]))
    tax = split_annual(Decimal(fin["tax_paid_inr_annual"]))
    debt = split_annual(loan_debt_annual)
    db = tmy_inputs.get("meteo_data", {})
    assumptions = {
        "loss_register": plant["loss_register"],
        "uncertainty": unc,
        "model_version": model.MODEL_VERSION,
        "weather_basis": {
            "source": "pvgis_tmy",
            "radiation_db": db.get("radiation_db"),
            "year_min": db.get("year_min"),
            "year_max": db.get("year_max"),
            "restamp": "hh:00 UTC is the hour midpoint (components close there); Feb 29 repeats Feb 28 (D21)",
        },
        "tariff_inr_per_kwh": str(tariff),
        "maintenance_capex_inr_annual": fin["maintenance_capex_inr_annual"],
    }
    rows = []
    for i, (month, r) in enumerate(m.iterrows()):
        p50 = Decimal(repr(float(r["p50_kwh"]))).quantize(Decimal("0.1"))
        rows.append(
            {
                "id": stable_uuid("baseline", plant["id"], version, month),
                "plant_id": plant["id"],
                "version": version,
                "status": "draft",
                "valid_month": month,
                "energy_p50_kwh": p50,
                "energy_p90_kwh": (p50 * p90_factor).quantize(Decimal("0.1")),
                "revenue_p50_inr": quantize_inr(p50 * tariff),
                "opex_inr": opex[i],
                "tax_inr": tax[i],
                "debt_service_inr": debt[i],
                "assumptions": assumptions | {"ep_dp_kwh": round(float(r["ep_dp_kwh"]), 1)},
                "approved_at": None,
                "approved_by": None,
                "reason": cfg["approval"]["reason"],
                "supersedes": supersedes,
            }
        )
    summary = {
        "p50_monthly": [float(r["energy_p50_kwh"]) for r in rows],
        "p50_annual": float(sum(r["energy_p50_kwh"] for r in rows)),
        "p90_annual": float(sum(r["energy_p90_kwh"] for r in rows)),
        "revenue_p50_inr": str(sum(r["revenue_p50_inr"] for r in rows)),
    }
    return rows, summary


def save_draft(conn: Connection, rows: list[dict]) -> None:
    """Replace an existing DRAFT of this version; approved rows are refused by the trigger."""
    v = rows[0]["version"]
    plant_id = rows[0]["plant_id"]
    status = (
        conn.execute(
            text("SELECT DISTINCT status FROM baseline WHERE plant_id = :p AND version = :v"), {"p": plant_id, "v": v}
        )
        .scalars()
        .all()
    )
    if "approved" in status:
        raise BaselineError(f"baseline v{v} is approved and immutable; build a new version")
    conn.execute(
        text("DELETE FROM baseline WHERE plant_id = :p AND version = :v AND status = 'draft'"), {"p": plant_id, "v": v}
    )
    copy_frame(conn, "baseline", pd.DataFrame(rows))


def next_version(conn: Connection, plant_id: str) -> tuple[int, int | None]:
    """Reuse the open draft's version; otherwise max approved + 1 (superseding it)."""
    rows = conn.execute(
        text(
            "SELECT version, bool_and(status = 'approved') FROM baseline WHERE plant_id = :p "
            "GROUP BY version ORDER BY version"
        ),
        {"p": plant_id},
    ).all()
    if not rows:
        return 1, None
    drafts = [v for v, approved in rows if not approved]
    if drafts:
        return drafts[-1], (rows[-2][0] if len(rows) > 1 else None)
    return rows[-1][0] + 1, rows[-1][0]


def approve(conn: Connection, plant_id: str, version: int, approved_by: str, reason: str | None = None) -> int:
    n = conn.execute(
        text(
            "UPDATE baseline SET status = 'approved', approved_at = :t, approved_by = :b, "
            "reason = coalesce(:r, reason) WHERE plant_id = :p AND version = :v AND status = 'draft'"
        ),
        {"t": datetime.now(UTC), "b": approved_by, "r": reason, "p": plant_id, "v": version},
    ).rowcount
    if n == 0:
        raise BaselineError(f"no draft rows for {plant_id} v{version}")
    return n


def versions(conn: Connection, plant_id: str) -> list[dict]:
    rows = (
        conn.execute(
            text(
                "SELECT version, min(status) AS status, min(approved_by) AS approved_by, "
                "min(approved_at) AS approved_at, "
                "min(reason) AS reason, min(supersedes) AS supersedes, sum(energy_p50_kwh) AS p50_kwh, "
                "sum(energy_p90_kwh) AS p90_kwh, sum(revenue_p50_inr) AS revenue_p50_inr, count(*) AS months "
                "FROM baseline WHERE plant_id = :p GROUP BY version ORDER BY version"
            ),
            {"p": plant_id},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def approved_months(conn: Connection, plant_id: str, year: int) -> pd.DataFrame:
    """Latest approved version's rows for a year (finance reads opex/tax/debt; CFO lens reads P50/P90)."""
    v = conn.execute(
        text("SELECT max(version) FROM baseline WHERE plant_id = :p AND status = 'approved'"), {"p": plant_id}
    ).scalar_one()
    if v is None:
        raise BaselineError(f"no approved baseline for {plant_id}; run `make baseline` then `make approve-baseline`")
    return pd.read_sql(
        text(
            "SELECT * FROM baseline WHERE plant_id = :p AND version = :v AND "
            "valid_month >= :a AND valid_month < :b ORDER BY valid_month"
        ),
        conn,
        params={"p": plant_id, "v": v, "a": date(year, 1, 1), "b": date(year + 1, 1, 1)},
    )
