"""Work orders, SLA clock, priority, MTTR (docs/02 §8.3).

Auto-created for every confirmed outage (critical) and suspected underperformance (major). Lifecycle timestamps come
from the operator log. priority = loss_rate × severity_weight × (1 + 0.5 × sla_age_ratio), evaluated at the end of
the record (restored, or the end of data for open orders) — D23.
"""

import pandas as pd

from app.contracts.loader import OM

SEVERITY_WEIGHT = {"critical": 1.0, "major": 0.6, "minor": 0.3}
SLA_FACTOR = 0.5
ORDER = ["open", "acknowledged", "onsite", "restored", "verified"]


def severity(event) -> str | None:
    if event.category == "equipment_outage" and event.confidence == "confirmed":
        return "critical"
    if event.category == "underperformance":
        return "major"
    return None


def build(events: pd.DataFrame, oplog: pd.DataFrame, loss_rate: dict, data_end: pd.Timestamp, om: OM) -> list[dict]:
    rows = []
    for e in events.itertuples():
        sev = severity(e)
        if sev is None:
            continue
        end = e.end_ts if pd.notna(e.end_ts) else data_end
        log = oplog[
            (oplog["asset_id"] == e.asset_id)
            & (oplog["at"] >= e.start_ts)
            & (oplog["at"] <= end + pd.Timedelta(hours=1))
            & (oplog["kind"] != "cleaning")
        ]
        stamps = {k: log.loc[log["kind"] == k, "at"].min() for k in ("acknowledged", "onsite", "restored", "verified")}
        stamps = {k: (v if pd.notna(v) else None) for k, v in stamps.items()}
        status = "open"
        for k in ORDER[1:]:
            if stamps.get(k) is not None:
                status = k
        restore_h = float(om.sla[sev]["restore_h"])
        stop = stamps["restored"] or data_end
        elapsed_h = (stop - e.start_ts).total_seconds() / 3600
        age_ratio = elapsed_h / restore_h
        rate = float(loss_rate.get(e.id, 0.0))
        priority = rate * SEVERITY_WEIGHT[sev] * (1 + SLA_FACTOR * age_ratio)
        rows.append(
            {
                "event_id": e.id,
                "severity": sev,
                "status": status,
                "opened_at": e.start_ts,
                "acked_at": stamps["acknowledged"],
                "onsite_at": stamps["onsite"],
                "restored_at": stamps["restored"],
                "verified_at": stamps["verified"],
                "priority_score": priority,
                "priority_inputs": {
                    "loss_rate_kwh_per_h": round(rate, 3),
                    "severity_weight": SEVERITY_WEIGHT[sev],
                    "sla_factor": SLA_FACTOR,
                    "sla_age_ratio": round(age_ratio, 4),
                    "elapsed_h": round(elapsed_h, 2),
                    "restore_h": restore_h,
                    "sla_breached": elapsed_h > restore_h,
                    "ack_h_sla": om.sla[sev]["ack_h"],
                    "onsite_h_sla": om.sla[sev]["onsite_h"],
                },
                "source_kind": "synthetic_scenario" if len(log) else "derived",
            }
        )
    return rows


def mttr_h(work_orders: pd.DataFrame) -> float | None:
    closed = work_orders.dropna(subset=["restored_at"])
    if closed.empty:
        return None
    return float(((closed["restored_at"] - closed["opened_at"]).dt.total_seconds() / 3600).mean())


def sla_breaches(work_orders: pd.DataFrame) -> int:
    return int(sum(1 for p in work_orders["priority_inputs"] if p["sla_breached"]))
