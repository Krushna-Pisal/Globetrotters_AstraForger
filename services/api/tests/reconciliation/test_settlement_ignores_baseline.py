"""T-SET-03 / T-REC-04: mutating the baseline (new version with ×1.5 energy) leaves every settlement line identical.
Plus static guards: settlement and accounting never mention the baseline table; LD money never in settlement."""

import re
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from app.core.bulk import copy_frame, upsert_dataset
from app.settlement import ledger as settlement

pytestmark = pytest.mark.db
APP = Path(__file__).resolve().parents[2] / "app"
DS = "recon_settlement_test"


def _ledger_rows():
    rows = []
    for m in range(1, 13):
        rows.append(
            {
                "dataset_id": DS,
                "plant_id": "THAR1",
                "period_month": date(2024, m, 1),
                "meter_kwh": 8.5e6 + m * 1e5,
                "inverter_sum_kwh": 8.63e6,
                "export_loss_kwh": 1.3e5,
                "accountable_kwh": 8.5e6 + m * 1e5,
                "recon_delta_pct": 0.001,
                "rule_refs": {},
                "hours_with_generation": 330.0,
                "backdown_hours": 40.0 if m == 10 else 0.0,
                "grid_unavail_hours_counted": 6.0 if m in (6, 11) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _baseline(version: int, scale: float):
    return pd.DataFrame(
        [
            {
                "id": uuid.uuid4(),
                "plant_id": "THAR1",
                "version": version,
                "status": "approved",
                "valid_month": date(2024, m, 1),
                "energy_p50_kwh": Decimal(str(9e6 * scale)),
                "energy_p90_kwh": Decimal(str(8e6 * scale)),
                "revenue_p50_inr": Decimal("22500000.00"),
                "opex_inr": Decimal("2750000.00"),
                "tax_inr": Decimal("583333.33"),
                "debt_service_inr": Decimal("14166666.67"),
                "assumptions": {},
                "approved_at": None,
                "approved_by": "test",
                "reason": "test",
                "supersedes": None,
            }
            for m in range(1, 13)
        ]
    )


def _lines(conn):
    return conn.execute(
        text(
            "SELECT kind, period_start, qty_kwh, rate_inr_per_kwh, amount_inr, inputs::text, "
            "provisional FROM settlement_line WHERE dataset_id = :d ORDER BY 1, 2"
        ),
        {"d": DS},
    ).all()


def test_settlement_identical_after_baseline_change(migrated_engine):
    with migrated_engine.begin() as conn:
        upsert_dataset(conn, DS, "THAR1", "synthetic", {}, seed=1)
        conn.execute(text("DELETE FROM accounting_ledger WHERE dataset_id = :d"), {"d": DS})
        copy_frame(conn, "accounting_ledger", _ledger_rows())
        conn.execute(text("DELETE FROM baseline WHERE plant_id = 'THAR1' AND version IN (91, 92) AND status = 'draft'"))
        copy_frame(conn, "baseline", _baseline(91, 1.0))
        settlement.run(conn, DS)
        before = _lines(conn)
        copy_frame(conn, "baseline", _baseline(92, 1.5))
        settlement.run(conn, DS)
        after = _lines(conn)
    assert before == after
    assert {r.kind for r in before} == {
        "energy_charge",
        "backdown_comp",
        "excess_repricing",
        "grid_unavail_comp",
        "shortfall_comp",
    }


def test_settlement_totals_are_sums_of_quantized_lines(migrated_engine):
    with migrated_engine.connect() as conn:
        lines = conn.execute(text("SELECT amount_inr FROM settlement_line WHERE dataset_id = :d"), {"d": DS}).scalars()
        amounts = list(lines)
        total = sum(settlement.total(conn, DS, date(2024, m, 1)) for m in range(1, 13))
    assert all(a == a.quantize(Decimal("0.01")) for a in amounts)
    assert total == sum(amounts)


@pytest.mark.parametrize("package", ["settlement", "accounting"])
def test_no_baseline_or_om_reference_in_settlement_sql(package):
    for f in (APP / package).glob("*.py"):
        body = f.read_text(encoding="utf-8")
        assert not re.search(r"\bFROM\s+baseline\b|\bJOIN\s+baseline\b", body, re.I), f
        assert "om_ld_line" not in body, f
