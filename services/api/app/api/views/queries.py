"""Read helpers over stored engine outputs for the role views (aggregation only; the engines did the physics)."""

import pandas as pd
from sqlalchemy import Connection, text

from app.api.views.common import Period

LOCAL_DAY = "(ts_start AT TIME ZONE 'Asia/Kolkata')::date"
LOCAL_MONTH = "date_trunc('month', ts_start AT TIME ZONE 'Asia/Kolkata')::date"


def _df(conn: Connection, sql: str, **params) -> pd.DataFrame:
    df = pd.read_sql(text(sql), conn, params=params)
    for c in (
        "start_ts",
        "end_ts",
        "ts_start",
        "at",
        "opened_at",
        "acked_at",
        "onsite_at",
        "restored_at",
        "verified_at",
    ):
        if c in df:
            df[c] = pd.to_datetime(df[c], utc=True)
    return df


def daily_energy(conn: Connection, dataset_id: str, p: Period) -> pd.DataFrame:
    return _df(
        conn,
        f"""
        WITH x AS (SELECT {LOCAL_DAY} AS d, sum(e_potential_kwh) AS ep, max(band_rel) AS band FROM expected_output
                   WHERE dataset_id = :ds AND ts_start >= :a AND ts_start < :b GROUP BY 1),
             y AS (SELECT {LOCAL_DAY} AS d, sum(e_kwh) AS ea, count(*) FILTER (WHERE quality = 'no_data') AS nd
                   FROM actual_output WHERE dataset_id = :ds AND ts_start >= :a AND ts_start < :b GROUP BY 1)
        SELECT x.d, x.ep, x.band, y.ea, coalesce(y.nd, 0) AS no_data FROM x LEFT JOIN y USING (d) ORDER BY 1""",
        ds=dataset_id,
        a=p.start_utc,
        b=p.end_utc,
    )


def monthly_energy(conn: Connection, dataset_id: str) -> pd.DataFrame:
    return _df(
        conn,
        f"""
        WITH x AS (SELECT {LOCAL_MONTH} AS m, sum(e_potential_kwh) AS ep FROM expected_output WHERE dataset_id = :ds
                   GROUP BY 1),
             y AS (SELECT {LOCAL_MONTH} AS m, sum(e_kwh) AS ea FROM actual_output WHERE dataset_id = :ds GROUP BY 1)
        SELECT x.m, x.ep, y.ea FROM x LEFT JOIN y USING (m) ORDER BY 1""",
        ds=dataset_id,
    )


def events(conn: Connection, dataset_id: str, p: Period | None = None) -> pd.DataFrame:
    sql = (
        "SELECT e.id::text AS id, e.asset_id, e.category::text AS category, e.cause_code, e.start_ts, e.end_ts, "
        "e.controllable, e.confidence::text AS confidence, e.evidence, e.setpoint_kw, w.id::text AS work_order_id, "
        "w.status::text AS wo_status FROM event e LEFT JOIN work_order w ON w.event_id = e.id "
        "WHERE e.dataset_id = :ds"
    )
    params: dict = {"ds": dataset_id}
    if p is not None:
        sql += " AND e.start_ts < :b AND coalesce(e.end_ts, 'infinity') > :a"
        params |= {"a": p.start_utc, "b": p.end_utc}
    return _df(conn, sql + " ORDER BY e.start_ts", **params)


def event_gap_kwh(conn: Connection, dataset_id: str, asset_id: str, start, end, clip: Period | None = None) -> float:
    """Σ (E_potential − actual) over the event window (inverter events: that inverter; plant events: all)."""
    a, b = start, end if end is not None and not pd.isna(end) else pd.Timestamp.max.tz_localize("UTC")
    if clip is not None:
        a, b = max(a, clip.start_utc), min(b, clip.end_utc)
        if a >= b:
            return 0.0
    asset_filter = "AND x.asset_id = :asset" if "/" in asset_id else ""
    v = conn.execute(
        text(f"""
        SELECT coalesce(sum(x.e_potential_kwh - coalesce(y.e_kwh, 0)), 0) FROM expected_output x
        LEFT JOIN actual_output y ON y.dataset_id = x.dataset_id AND y.asset_id = x.asset_id AND y.ts_start = x.ts_start
        WHERE x.dataset_id = :ds AND x.ts_start >= :a AND x.ts_start < :b {asset_filter}"""),
        {"ds": dataset_id, "a": a, "b": b, "asset": asset_id},
    ).scalar_one()
    return float(v)


def trace(conn: Connection, dataset_id: str, asset_id: str, a, b) -> pd.DataFrame:
    if "/" in asset_id:
        return _df(
            conn,
            """
            SELECT x.ts_start, x.e_potential_kwh AS ep, y.e_kwh AS ea, y.quality::text AS quality, y.status,
                   x.band_rel AS band, x.clipped
            FROM expected_output x LEFT JOIN actual_output y
              ON y.dataset_id = x.dataset_id AND y.asset_id = x.asset_id AND y.ts_start = x.ts_start
            WHERE x.dataset_id = :ds AND x.asset_id = :asset AND x.ts_start >= :a AND x.ts_start < :b
            ORDER BY 1""",
            ds=dataset_id,
            asset=asset_id,
            a=a,
            b=b,
        )
    return _df(
        conn,
        """
        WITH x AS (SELECT ts_start, sum(e_potential_kwh) AS ep, max(band_rel) AS band, bool_or(clipped) AS clipped
                   FROM expected_output WHERE dataset_id = :ds AND ts_start >= :a AND ts_start < :b GROUP BY 1),
             y AS (SELECT ts_start, sum(e_kwh) AS ea FROM actual_output
                   WHERE dataset_id = :ds AND ts_start >= :a AND ts_start < :b GROUP BY 1)
        SELECT x.ts_start, x.ep, y.ea, NULL AS quality, NULL AS status, x.band, x.clipped
        FROM x LEFT JOIN y USING (ts_start) ORDER BY 1""",
        ds=dataset_id,
        a=a,
        b=b,
    )


def month_actual(conn: Connection, dataset_id: str, p: Period) -> pd.DataFrame:
    return _df(
        conn,
        "SELECT asset_id, ts_start, e_kwh, quality::text AS quality, status FROM actual_output "
        "WHERE dataset_id = :ds AND ts_start >= :a AND ts_start < :b",
        ds=dataset_id,
        a=p.start_utc,
        b=p.end_utc,
    )


def month_poa(conn: Connection, dataset_id: str, p: Period) -> pd.Series:
    df = _df(
        conn,
        "SELECT ts_start, max(poa_wm2) AS poa FROM expected_output WHERE dataset_id = :ds "
        "AND ts_start >= :a AND ts_start < :b GROUP BY 1",
        ds=dataset_id,
        a=p.start_utc,
        b=p.end_utc,
    )
    return df.set_index("ts_start")["poa"]


def ws_quality(conn: Connection, dataset_id: str, p: Period) -> tuple[pd.Series, pd.Series]:
    df = _df(
        conn,
        "SELECT ts_start, value, quality::text AS quality FROM measurement WHERE dataset_id = :ds "
        "AND quantity = 'poa_wm2' AND ts_start >= :a AND ts_start < :b",
        ds=dataset_id,
        a=p.start_utc,
        b=p.end_utc,
    )
    s = df.set_index("ts_start")
    return s["value"], s["quality"].eq("ok")


def om_line(conn: Connection, dataset_id: str):
    return conn.execute(text("SELECT * FROM om_ld_line WHERE dataset_id = :ds"), {"ds": dataset_id}).mappings().first()


def cleanings(conn: Connection, dataset_id: str) -> list:
    rows = (
        conn.execute(
            text("SELECT at FROM operator_log WHERE dataset_id = :ds AND kind = 'cleaning' ORDER BY at"),
            {"ds": dataset_id},
        )
        .scalars()
        .all()
    )
    return [pd.Timestamp(r).tz_convert("Asia/Kolkata").date() for r in rows]
