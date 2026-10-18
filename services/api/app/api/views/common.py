"""Shared pieces of the role views (D31: prototype projections over M1–M3 engine outputs until the M4/M5 registry).

Every number is computed on the server; the web app only renders the `display` strings and chart arrays.
Each payload is checked by `guard` before it leaves: metric ids outside the role's lens, money words in the
Engineer/Operations views and inverter ids in the CFO view are refused (500, audited), never shipped.
"""

import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import lru_cache

import pandas as pd
import yaml
from fastapi import HTTPException, status
from sqlalchemy import Connection, text

from app.core.bulk import audit
from app.core.config import get_settings
from app.core.lineage import sha256_hash
from app.core.timeutil import PLANT_TZ

LENSES = ("engineer", "operations", "cfo")
MODE_LABEL = {"synthetic": "SYNTHETIC SCENARIO", "measured": "MEASURED"}


@lru_cache
def lens_spec(lens: str) -> dict:
    return yaml.safe_load((get_settings().configs_dir / "lenses" / f"{lens}.yaml").read_text(encoding="utf-8"))


@lru_cache
def all_metric_ids() -> tuple[str, ...]:
    cfg = yaml.safe_load((get_settings().configs_dir / "metrics" / "metrics.yaml").read_text(encoding="utf-8"))
    return tuple(m["id"] for m in cfg["metrics"])


# ---------------------------------------------------------------- small read cache
_CACHE: dict[tuple, tuple[float, object]] = {}
CACHE_TTL_S = 120.0


def cached(key: tuple, fn):
    """Short in-process cache for whole-dataset aggregates (they only change when the pipeline re-runs)."""
    import time

    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]
    value = fn()
    _CACHE[key] = (time.monotonic(), value)
    return value


# ---------------------------------------------------------------- periods and datasets
@dataclass(frozen=True)
class Period:
    month: date
    start_utc: pd.Timestamp
    end_utc: pd.Timestamp

    @property
    def label(self) -> str:
        return self.month.strftime("%Y-%m")


def parse_period(period: str) -> Period:
    try:
        if len(period) != 7:
            raise ValueError(period)
        m = date.fromisoformat(f"{period}-01")
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="period must be YYYY-MM") from exc
    start = pd.Timestamp(m).tz_localize(PLANT_TZ)
    end = (start + pd.offsets.MonthBegin(1)).tz_convert("UTC")
    return Period(m, start.tz_convert("UTC"), end)


def dataset_info(conn: Connection, dataset_id: str) -> dict:
    row = (
        conn.execute(text("SELECT id, plant_id, kind FROM dataset WHERE id = :d"), {"d": dataset_id}).mappings().first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    months = (
        conn.execute(
            text(
                "SELECT DISTINCT date_trunc('month', ts_start AT TIME ZONE 'Asia/Kolkata')::date AS m "
                "FROM actual_output WHERE dataset_id = :d ORDER BY 1"
            ),
            {"d": dataset_id},
        )
        .scalars()
        .all()
    )
    return {
        "id": row["id"],
        "plant_id": row["plant_id"],
        "kind": row["kind"],
        "mode": {
            "kind": "synthetic_scenario" if row["kind"] == "synthetic" else "measured",
            "label": f"{MODE_LABEL[row['kind']]} · {row['id']}",
        },
        "periods": [m.strftime("%Y-%m") for m in months],
    }


def asset_names(conn: Connection, plant_id: str) -> dict[str, str]:
    rows = conn.execute(text("SELECT id, name FROM asset WHERE plant_id = :p"), {"p": plant_id}).all()
    return {r.id: r.name for r in rows}


# ---------------------------------------------------------------- formatting (server-side, D31)
def fmt_energy(kwh: float | None, unit: str) -> str:
    if kwh is None or (isinstance(kwh, float) and pd.isna(kwh)):
        return "—"
    if unit == "kWh":
        return f"{kwh:,.0f} kWh"
    if unit == "MWh":
        return f"{kwh / 1e3:,.1f} MWh"
    return f"{kwh / 1e6:,.2f} GWh"


def fmt_inr(amount: Decimal | float | None) -> str:
    if amount is None:
        return "—"
    a = float(amount)
    sign = "−" if a < 0 else ""
    a = abs(a)
    if a >= 1e7:
        return f"{sign}₹{a / 1e7:,.2f} cr"
    if a >= 1e5:
        return f"{sign}₹{a / 1e5:,.2f} lakh"
    return f"{sign}₹{a:,.0f}"


def fmt_pct(x: float | None, places: int = 1) -> str:
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{places}f} %"


def fmt_ts(ts) -> str | None:
    if ts is None or pd.isna(ts):
        return None
    return pd.Timestamp(ts).tz_convert(PLANT_TZ).strftime("%Y-%m-%d %H:%M")


def card(
    metric_id: str,
    label: str,
    value,
    unit: str,
    display: str,
    *,
    source_kind: str = "derived",
    provisional: bool = False,
    compare: dict | None = None,
    chip: str | None = None,
    status_: str | None = None,
    hint: str | None = None,
) -> dict:
    """MetricCard (docs/05 §2). `status` is ok | warn | alert | info for the tile accent."""
    return {
        "metric_id": metric_id,
        "label": label,
        "value": None if value is None else str(value),
        "unit": unit,
        "display": display,
        "source_kind": source_kind,
        "provisional": provisional,
        "compare": compare,
        "chip": chip,
        "status": status_ or "info",
        "hint": hint,
    }


def omissions(lens: str, present: set[str]) -> tuple[list[dict], dict]:
    """Omitted items with reasons, and the stripped-field receipt (count of omitted items that had data)."""
    omitted, kinds = [], {"metric": 0, "field": 0}
    for o in lens_spec(lens).get("omit", []):
        kind = "metric" if "metric" in o else "field"
        oid = o.get("metric") or o.get("field")
        omitted.append(
            {"kind": kind, "id": oid, "reason": o["reason"], **({"scope": o["scope"]} if "scope" in o else {})}
        )
        if oid in present:
            kinds[kind] += 1
    return omitted, {"count": sum(kinds.values()), "kinds": kinds}


# ---------------------------------------------------------------- guard
MONEY_TOKENS = ("₹", "tariff", "INR", "lakh", "crore")


def forbidden_ids(lens: str) -> set[str]:
    allowed = set(lens_spec(lens)["metrics"])
    return {m for m in all_metric_ids() if m not in allowed}


def guard(conn: Connection, lens: str, payload: dict, actor: str) -> None:
    """Refuse a payload that would leak outside the lens. The `omitted` list only names items; it is not scanned."""
    body = {k: v for k, v in payload.items() if k != "omitted"}
    blob = json.dumps(body, default=str, ensure_ascii=False)
    hits = [m for m in forbidden_ids(lens) if re.search(rf"\b{re.escape(m)}\b", blob)]
    if lens in ("engineer", "operations"):
        hits += [t for t in MONEY_TOKENS if t in blob]
    if lens == "cfo":
        hits += re.findall(r"\bINV-\d+\b", blob)[:3]
    if hits:
        audit(conn, actor, "lens.guard_violation", lens, {"hits": sorted(set(hits))})
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="lens_guard_violation")


def finish(conn: Connection, lens: str, payload: dict, actor: str) -> dict:
    guard(conn, lens, payload, actor)
    payload["meta"]["payload_hash"] = sha256_hash(
        {k: v for k, v in payload.items() if k != "meta"}
        | {"meta": {k: v for k, v in payload["meta"].items() if k not in ("generated_at", "payload_hash")}}
    )
    return payload


def meta(info: dict, lens: str, period: Period, extra: dict | None = None) -> dict:
    spec = lens_spec(lens)
    return {
        "plant_id": info["plant_id"],
        "dataset_id": info["id"],
        "period": period.label,
        "tz": PLANT_TZ,
        "mode": info["mode"],
        "lens": {"id": lens, "version": spec["version"], "spec_hash": sha256_hash(spec)},
        "periods": info["periods"],
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        **(extra or {}),
    }
