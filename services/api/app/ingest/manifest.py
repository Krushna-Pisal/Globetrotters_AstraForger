"""Source manifests (data/manifests/*.json) and source_batch rows. Every raw file is recorded with its sha256."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Connection, text

from app.core.bulk import stable_uuid
from app.core.config import get_settings


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(name: str, entry: dict) -> Path:
    """Write/merge one manifest file. Keys of `entry` overwrite earlier values."""
    path = get_settings().data_dir / "manifests" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    current.update(entry)
    path.write_text(json.dumps(current, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def register_batch(
    conn: Connection,
    dataset_id: str,
    source_name: str,
    sha256: str,
    source_kind: str,
    url: str | None = None,
    license: str | None = None,
    notes: str | None = None,
    retrieved_at: datetime | None = None,
):
    """Deterministic batch id per (dataset, source, content): re-ingesting the same file reuses the batch."""
    batch_id = stable_uuid("batch", dataset_id, source_name, sha256)
    conn.execute(
        text(
            "INSERT INTO source_batch (id, dataset_id, source_name, url, license, sha256, retrieved_at, source_kind, "
            "notes) "
            "VALUES (:i, :d, :n, :u, :l, :s, :r, :k, :no) ON CONFLICT (id) DO NOTHING"
        ),
        {
            "i": batch_id,
            "d": dataset_id,
            "n": source_name,
            "u": url,
            "l": license,
            "s": sha256,
            "r": retrieved_at or datetime.now(UTC),
            "k": source_kind,
            "no": notes,
        },
    )
    return batch_id
