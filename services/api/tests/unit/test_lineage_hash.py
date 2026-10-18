from datetime import UTC, datetime
from decimal import Decimal

from app.core.lineage import canonical_json, sha256_hash


def test_key_order_does_not_change_hash():
    assert sha256_hash({"a": 1, "b": {"c": 2, "d": 3}}) == sha256_hash({"b": {"d": 3, "c": 2}, "a": 1})


def test_value_change_changes_hash():
    assert sha256_hash({"v": Decimal("1.00")}) != sha256_hash({"v": Decimal("1.01")})


def test_canonical_form():
    ts = datetime(2024, 4, 9, 4, 45, tzinfo=UTC)
    assert canonical_json({"v": Decimal("2.50"), "t": ts}) == '{"t":"2024-04-09T04:45:00+00:00","v":"2.50"}'
    assert sha256_hash({}).startswith("sha256:")
