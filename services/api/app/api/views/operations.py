"""Operations view — "What do I fix first today, and is the O&M contractor meeting its SLA?"

Judged against weather-adjusted expected output and the O&M contract, never the baseline (invariant 11). Units: MWh.
"""

import pandas as pd
from sqlalchemy import Connection, text

from app.api.views import queries as q
from app.api.views.common import Period, asset_names, card, fmt_energy, fmt_pct, fmt_ts, lens_spec, meta, omissions
from app.contracts.loader import load_om
from app.om import cleaning

LENS = "operations"
NEXT = {"open": "acknowledged", "acknowledged": "onsite", "onsite": "restored", "restored": "verified"}


def work_orders(conn: Connection, dataset_id: str) -> pd.DataFrame:
    return q._df(
        conn,
        """
        SELECT w.id::text AS id, w.event_id::text AS event_id, w.severity, w.status::text AS status, w.opened_at,
               w.acked_at, w.onsite_at, w.restored_at, w.verified_at, w.priority_score, w.priority_inputs,
               e.asset_id, e.category::text AS category, e.cause_code, e.start_ts, e.end_ts, e.confidence::text AS conf
        FROM work_order w JOIN event e ON e.id = w.event_id WHERE e.dataset_id = :ds ORDER BY w.opened_at""",
        ds=dataset_id,
    )


def build(conn: Connection, info: dict, p: Period) -> dict:
    ds = info["id"]
    names = asset_names(conn, info["plant_id"])
    om_line = q.om_line(conn, ds)
    tiles, sections = [], {}
    if om_line is None:
        sections["unavailable"] = "No O&M contract is modelled for this dataset: work orders and SLA clocks need one."
    else:
        om = load_om()
        monthly = om_line["inputs"]["monthly"]
        cur = monthly.get(p.month.isoformat(), {})
        a_e = cur.get("a_e")
        months = sorted(monthly)
        ytd_keys = [m for m in months if m <= p.month.isoformat()]
        loss = sum(monthly[m]["loss_kwh"] for m in ytd_keys)
        ep = sum(monthly[m]["ep_eligible_kwh"] for m in ytd_keys)
        a_ytd = 1 - loss / ep if ep else None
        guarantee = float(om.guarantee)
        wos = work_orders(conn, ds)
        end = p.end_utc
        in_period = wos[(wos["opened_at"] < end) & ((wos["restored_at"].isna()) | (wos["restored_at"] >= p.start_utc))]
        open_at_end = wos[(wos["opened_at"] < end) & (wos["restored_at"].isna() | (wos["restored_at"] >= end))]
        closed = in_period.dropna(subset=["restored_at"])
        closed = closed[(closed["restored_at"] >= p.start_utc) & (closed["restored_at"] < end)]
        mttr = (
            float(((closed["restored_at"] - closed["opened_at"]).dt.total_seconds() / 3600).mean())
            if len(closed)
            else None
        )
        breaches = int(sum(1 for r in in_period.itertuples() if r.priority_inputs.get("sla_breached")))
        tiles = [
            card(
                "availability_energy",
                "Energy availability (month)",
                a_e,
                "fraction",
                fmt_pct(a_e, 2),
                status_="ok" if a_e is not None and a_e >= guarantee else "alert",
                provisional=True,
                compare={"against": "guarantee", "value": str(guarantee)},
                hint=f"guarantee {fmt_pct(guarantee, 1)} · O&M contract {om.id}",
            ),
            card(
                "availability_energy",
                "Energy availability (YTD)",
                a_ytd,
                "fraction",
                fmt_pct(a_ytd, 2),
                status_="ok" if a_ytd is not None and a_ytd >= guarantee else "alert",
                provisional=True,
                hint="annual assessment decides LDs",
            ),
            card(
                "open_work_orders",
                "Open work orders",
                len(open_at_end),
                "count",
                str(len(open_at_end)),
                status_="warn" if len(open_at_end) else "ok",
                hint=f"at end of {p.label}",
            ),
            card(
                "mttr_h",
                "Mean time to restore",
                mttr,
                "h",
                "—" if mttr is None else f"{mttr:.1f} h",
                hint=f"{len(closed)} restored this month",
            ),
            card(
                "sla_breaches",
                "SLA breaches",
                breaches,
                "count",
                str(breaches),
                status_="alert" if breaches else "ok",
                hint="restore beyond 96 h critical / 168 h major",
            ),
        ]
        sections["availability_vs_guarantee"] = {
            "a_e": a_e,
            "guarantee": guarantee,
            "months": [m[:7] for m in months],
            "trend": [monthly[m]["a_e"] for m in months],
        }
        items = []
        for r in in_period.sort_values("priority_score", ascending=False).itertuples():
            gap = q.event_gap_kwh(conn, ds, r.asset_id, r.start_ts, r.end_ts)
            pi = r.priority_inputs
            items.append(
                {
                    "id": r.id,
                    "event_id": r.event_id,
                    "asset": names.get(r.asset_id, r.asset_id),
                    "category": r.category,
                    "cause_code": r.cause_code,
                    "severity": r.severity,
                    "status": r.status,
                    "next_status": NEXT.get(r.status),
                    "opened": fmt_ts(r.opened_at),
                    "acknowledged": fmt_ts(r.acked_at),
                    "onsite": fmt_ts(r.onsite_at),
                    "restored": fmt_ts(r.restored_at),
                    "verified": fmt_ts(r.verified_at),
                    "lost_kwh": round(gap, 1),
                    "lost_display": fmt_energy(gap, "MWh"),
                    "loss_rate_kwh_per_h": pi.get("loss_rate_kwh_per_h"),
                    "loss_rate_display": f"{pi.get('loss_rate_kwh_per_h', 0) / 1000:.2f} MWh/h",
                    "sla_clock": {
                        "elapsed_h": pi.get("elapsed_h"),
                        "restore_h": pi.get("restore_h"),
                        "age_ratio": pi.get("sla_age_ratio"),
                        "breached": pi.get("sla_breached"),
                    },
                    "priority_score": round(float(r.priority_score or 0), 1),
                    "priority_inputs": pi,
                    "confidence": r.conf,
                }
            )
        sections["work_queue"] = {
            "weights": {"critical": 1.0, "major": 0.6, "minor": 0.3, "sla_factor": 0.5},
            "formula": lens_spec(LENS)["priority"]["formula"],
            "items": items,
        }
        logs = q.cleanings(conn, ds)
        missed = cleaning.missed_windows(logs, om.cleaning_interval_days)
        daily = q.daily_energy(conn, ds, p)
        sections["soiling_and_cleaning"] = {
            "interval_days": om.cleaning_interval_days,
            "cleanings_in_period": [str(c) for c in logs if c.strftime("%Y-%m") == p.label],
            "last_cleaning": str(max((c for c in logs if c.strftime("%Y-%m") <= p.label), default=None) or "—"),
            "next_scheduled": str(
                cleaning.next_scheduled([c for c in logs if c.strftime("%Y-%m") <= p.label], om.cleaning_interval_days)
                or "—"
            ),
            "missed": [
                {
                    "scheduled": str(m["scheduled"]),
                    "done_late_on": str(m["done_late_on"]),
                    "days_overdue": m["days_overdue"],
                }
                for m in missed
            ],
            "performance_index": {
                "days": [str(d) for d in daily["d"]],
                "values": (daily["ea"] / daily["ep"]).round(4).where(daily["ep"] > 0).tolist(),
            },
            "note": "Daily actual ÷ expected for the plant. A slow decline between cleanings is soiling; the "
            "attribution engine (M4) turns it into a soiling ratio and lost MWh.",
        }
        evs = q.events(conn, ds, p)
        curt = []
        for e in evs[evs["category"] == "curtailment"].itertuples():
            gap = q.event_gap_kwh(conn, ds, e.asset_id, e.start_ts, e.end_ts)
            curt.append(
                {
                    "id": e.id,
                    "start": fmt_ts(e.start_ts),
                    "end": fmt_ts(e.end_ts),
                    "setpoint_mw": None if pd.isna(e.setpoint_kw) else e.setpoint_kw / 1000,
                    "lost_display": fmt_energy(gap, "MWh"),
                    "lost_kwh": round(gap, 1),
                    "instruction": e.cause_code,
                }
            )
        sections["curtailment_log"] = {"items": curt}
    omitted, stripped = omissions(
        LENS,
        {"dscr", "cfads_inr", "revenue_settled_inr", "recoverable_inr", "energy_baseline_p50_kwh", "pr_25", "tariff"}
        if om_line is not None
        else {"tariff"},
    )
    return {
        "meta": meta(info, LENS, p),
        "decision": lens_spec(LENS)["decision"],
        "tiles": tiles,
        "sections": sections,
        "events": [],
        "omitted": omitted,
        "stripped": stripped,
    }


def transition(conn: Connection, wo_id: str, to: str, actor: str) -> dict:
    from datetime import UTC, datetime

    from app.core.bulk import audit

    row = conn.execute(
        text("SELECT status::text AS status FROM work_order WHERE id = CAST(:i AS uuid)"), {"i": wo_id}
    ).first()
    if row is None:
        return {"error": "not_found"}
    if NEXT.get(row.status) != to:
        return {"error": "invalid_transition", "from": row.status, "allowed": NEXT.get(row.status)}
    col = {"acknowledged": "acked_at", "onsite": "onsite_at", "restored": "restored_at", "verified": "verified_at"}[to]
    now = datetime.now(UTC)
    conn.execute(
        text(
            f"UPDATE work_order SET status = CAST(:s AS wo_status), {col} = coalesce({col}, :t) "  # noqa: S608
            "WHERE id = CAST(:i AS uuid)"
        ),
        {"s": to, "t": now, "i": wo_id},
    )
    audit(conn, actor, "workorder.transition", wo_id, {"from": row.status, "to": to})
    return {"id": wo_id, "from": row.status, "to": to, "at": now.isoformat()}
