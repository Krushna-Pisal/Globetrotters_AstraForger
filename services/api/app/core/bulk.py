"""Bulk table I/O: idempotent delete-and-insert via PostgreSQL COPY, plus the provenance guard (invariant 8)."""

import io
import json
import uuid
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd
from sqlalchemy import Connection, text

SYNTHETIC_KINDS = {"synthetic_scenario", "synthetic_reference", "synthetic_contract"}
NULL = r"\N"


def assert_provenance(dataset_kind: str, source_kinds: Iterable[str]) -> None:
    """Synthetic and measured data never share a dataset_id (invariant 8, T-DATA-03)."""
    kinds = set(source_kinds)
    if dataset_kind == "measured" and kinds & SYNTHETIC_KINDS:
        raise ValueError(f"synthetic source_kind {sorted(kinds & SYNTHETIC_KINDS)} in a measured dataset")
    if dataset_kind == "synthetic" and "measured" in kinds:
        raise ValueError("source_kind 'measured' in a synthetic dataset")


def dataset_kind(conn: Connection, dataset_id: str) -> str:
    return conn.execute(text("SELECT kind FROM dataset WHERE id = :d"), {"d": dataset_id}).scalar_one()


def _cell(value: Any) -> Any:
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=True, default=str)
    return value


def copy_frame(conn: Connection, table: str, df: pd.DataFrame) -> int:
    """COPY a DataFrame whose columns are table columns. dict/list cells are written as JSON."""
    if df.empty:
        return 0
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(_cell)
    buf = io.StringIO()
    out.to_csv(buf, index=False, header=False, na_rep=NULL, date_format="%Y-%m-%d %H:%M:%S%z")
    buf.seek(0)
    cols = ", ".join(out.columns)
    raw = conn.connection.driver_connection
    with raw.cursor() as cur, cur.copy(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '{NULL}')") as cp:
        while chunk := buf.read(1 << 20):
            cp.write(chunk)
    return len(out)


def replace_rows(conn: Connection, table: str, where: Mapping[str, Any], df: pd.DataFrame) -> int:
    """Idempotent write: delete rows matching `where`, then COPY `df` (docs/03 §3)."""
    clause = " AND ".join(f"{k} = :{k}" for k in where)
    conn.execute(text(f"DELETE FROM {table} WHERE {clause}"), dict(where))  # noqa: S608 - identifiers are internal
    return copy_frame(conn, table, df)


def write_measurements(conn: Connection, dataset_id: str, df: pd.DataFrame, assets: Iterable[str] | None = None) -> int:
    """Upsert-equivalent for measurements of the given assets (all assets in df by default)."""
    assert_provenance(dataset_kind(conn, dataset_id), df["source_kind"].unique())
    asset_ids = sorted(set(assets) if assets is not None else set(df["asset_id"]))
    conn.execute(
        text("DELETE FROM measurement WHERE dataset_id = :d AND asset_id = ANY(:a)"), {"d": dataset_id, "a": asset_ids}
    )
    return copy_frame(conn, "measurement", df)


def upsert_dataset(conn: Connection, dataset_id: str, plant_id: str, kind: str, config: dict, seed: int | None) -> None:
    conn.execute(
        text(
            "INSERT INTO dataset (id, plant_id, kind, seed, config) VALUES (:id, :p, :k, :s, CAST(:c AS jsonb)) "
            "ON CONFLICT (id) DO UPDATE SET config = EXCLUDED.config, seed = EXCLUDED.seed"
        ),
        {"id": dataset_id, "p": plant_id, "k": kind, "s": seed, "c": json.dumps(config, default=str)},
    )
    existing = dataset_kind(conn, dataset_id)
    if existing != kind:
        raise ValueError(f"dataset {dataset_id} is {existing}, cannot reuse it as {kind}")


def stable_uuid(*parts: Any) -> uuid.UUID:
    """Deterministic ids so re-runs produce identical rows (T-REPRO-01)."""
    return uuid.uuid5(uuid.NAMESPACE_URL, "ps4:" + "|".join(str(p) for p in parts))


def audit(conn: Connection, actor: str, action: str, obj: str, detail: dict) -> None:
    conn.execute(
        text("INSERT INTO audit_event (id, actor, action, object, detail) VALUES (:i, :a, :ac, :o, CAST(:d AS jsonb))"),
        {"i": uuid.uuid4(), "a": actor, "ac": action, "o": obj, "d": json.dumps(detail, default=str)},
    )
