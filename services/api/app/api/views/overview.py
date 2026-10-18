"""Plant overview, shared by every role: plant facts and dataset provenance; no money and no diagnostics.
The presenter additionally sees which lens verdicts agree per month (the three truths side by side)."""

from decimal import Decimal

import pandas as pd
from sqlalchemy import Connection, text

from app.api.views import queries as q
from app.api.views.common import cached, fmt_energy, fmt_pct
from app.performance import kpi
from app.twin.loader import load_plant


def build(conn: Connection, info: dict, role: str) -> dict:
    plant = load_plant(info["plant_id"])
    cap = plant.get("capacity", {})
    inv = plant.get("inverter", {})
    loc = plant.get("location", {})
    counts = conn.execute(
        text("SELECT category::text, count(*) FROM event WHERE dataset_id = :d GROUP BY 1"), {"d": info["id"]}
    ).all()
    facts = [
        {"label": "Plant", "value": plant["name"]},
        {"label": "DC capacity", "value": f"{cap['dc_kwp'] / 1000:,.0f} MWp" if cap.get("dc_kwp") else "not published"},
        {"label": "AC capacity", "value": f"{cap['ac_kw'] / 1000:,.0f} MW" if cap.get("ac_kw") else "not published"},
        {"label": "Inverters", "value": str(inv.get("count", "—"))},
        {
            "label": "Location",
            "value": f"{loc['lat']:.2f}° N, {loc['lon']:.2f}° E" if loc.get("lat") else "not published",
        },
        {"label": "Commercial operation", "value": str(plant.get("cod", "—"))},
        {
            "label": "Mounting",
            "value": f"fixed tilt {plant['array']['tilt_deg']}° south" if plant.get("array") else "—",
        },
    ]
    sources = conn.execute(
        text(
            "SELECT source_name, source_kind::text, sha256, coalesce(license,'') FROM source_batch "
            "WHERE dataset_id = :d ORDER BY source_name"
        ),
        {"d": info["id"]},
    ).all()
    payload = {
        "dataset": info,
        "plant": {
            "id": info["plant_id"],
            "name": plant["name"],
            "facts": facts,
            "synthetic": info["kind"] == "synthetic",
        },
        "events_by_category": {c: n for c, n in counts},
        "sources": [{"name": s[0], "source_kind": s[1], "sha256": s[2][:12], "license": s[3]} for s in sources],
        "lens_verdicts": None,
    }
    if role == "presenter" and info["kind"] == "synthetic":
        payload["lens_verdicts"] = verdicts(conn, info, plant)
    return payload


def verdicts(conn: Connection, info: dict, plant: dict) -> dict:
    """docs/02 §10 truth divergence: Engineer PI ≥ 0.98, Ops A_E ≥ 0.990, CFO settled revenue ≥ P50 revenue."""
    pr = cached(
        ("pr", info["id"]),
        lambda: kpi.monthly_pr(
            conn,
            info["id"],
            plant["inverter"]["dc_kwp_each"] * plant["inverter"]["count"],
            plant["module"]["gamma_pdc_per_c"],
        ),
    ).set_index("month")
    om = q.om_line(conn, info["id"])
    fin = pd.read_sql(
        text(
            "SELECT f.period_month, f.revenue_settled_inr, b.revenue_p50_inr FROM finance_period f "
            "JOIN baseline b ON b.valid_month = f.period_month AND b.status = 'approved' "
            "WHERE f.dataset_id = :d ORDER BY 1"
        ),
        conn,
        params={"d": info["id"]},
    )
    rows = []
    for r in fin.itertuples():
        m = r.period_month
        pi = float(pr.loc[m, "performance_index"]) if m in pr.index else None
        a_e = om["inputs"]["monthly"].get(m.isoformat(), {}).get("a_e") if om else None
        ratio = float(Decimal(r.revenue_settled_inr) / Decimal(r.revenue_p50_inr))
        e, o, c = pi is not None and pi >= 0.98, a_e is not None and a_e >= 0.99, ratio >= 1
        rows.append(
            {
                "month": m.strftime("%Y-%m"),
                "engineer": {"ok": e, "display": f"index {pi:.3f}" if pi is not None else "—"},
                "operations": {"ok": o, "display": fmt_pct(a_e, 2)},
                "cfo": {"ok": c, "display": f"{(ratio - 1) * 100:+.1f} % vs P50"},
                "diverge": len({e, o, c}) > 1,
            }
        )
    return {
        "rule": "Engineer: performance index ≥ 0.98 · Ops: availability ≥ 99.0 % · CFO: settled revenue ≥ P50",
        "months": rows,
        "note": "Where lenses disagree, the bridges (M4) name the steps that explain it — usually weather.",
    }


def energy_summary(conn: Connection, info: dict) -> dict:
    m = q.monthly_energy(conn, info["id"])
    return {
        "months": [x.strftime("%Y-%m") for x in m["m"]],
        "expected_display": fmt_energy(float(m["ep"].sum()), "GWh"),
        "actual_display": fmt_energy(float(m["ea"].sum()), "GWh"),
    }
