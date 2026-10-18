"""Canonical JSON and sha256 hashing for lineage (docs/04 §7 metric_value.lineage_hash, docs/05 payload_hash)."""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def _default(obj: Any) -> str:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime | date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"not canonically serialisable: {type(obj).__name__}")


def canonical_json(obj: Any) -> str:
    """Sorted keys, no whitespace, UTF-8 text; Decimal/date/UUID serialised as strings."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_default)


def sha256_hash(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
