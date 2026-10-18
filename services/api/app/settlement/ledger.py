"""PPA settlement engine: accounting_ledger + PPA -> settlement_line (docs/02 §6, metric revenue_settled_inr).

Monthly lines (C4.1, C4.4) are provisional until the year is complete; the annual true-up lines (C4.2, C4.3, C4.5)
are written only when all twelve months of the contract year are in the ledger.
"""

import calendar
from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import Connection, text

from app.accounting.ledger import read_ledger
from app.contracts.loader import PPA, load_ppa, register
from app.core.bulk import replace_rows, stable_uuid
from app.settlement import clauses


def hours_in_year(year: int) -> Decimal:
    return Decimal(8784 if calendar.isleap(year) else 8760)


def build_lines(ledger: pd.DataFrame, ppa: PPA, dataset_id: str, plant_id: str) -> list[dict]:
    rows = []
    for year, months in ledger.groupby(ledger["period_month"].map(lambda d: d.year)):
        complete = len(months) == 12
        deemed_backdown = Decimal("0")
        for r in months.sort_values("period_month").itertuples():
            acc = clauses.dec(r.accountable_kwh)
            hrs = clauses.dec(r.hours_with_generation)
            bd = clauses.dec(r.backdown_hours)
            ec = clauses.energy_charge(acc, ppa)
            bc = clauses.backdown_comp(acc, hrs, bd, ppa)
            deemed_backdown += Decimal(bc.inputs["deemed_kwh"])
            for line in (ec, bc):
                rows.append(_row(line, dataset_id, plant_id, r.period_month, "month", ppa, provisional=not complete))
        if complete:
            acc_y = sum((clauses.dec(v) for v in months["accountable_kwh"]), Decimal("0"))
            hrs_y = sum((clauses.dec(v) for v in months["hours_with_generation"]), Decimal("0"))
            grid_h = sum((clauses.dec(v) for v in months["grid_unavail_hours_counted"]), Decimal("0"))
            lines, _ = clauses.annual_lines(acc_y, hrs_y, hours_in_year(year), deemed_backdown, grid_h, ppa)
            for line in lines:
                rows.append(_row(line, dataset_id, plant_id, date(year, 1, 1), "year", ppa, provisional=False))
    return rows


def _row(line: clauses.Line, dataset_id: str, plant_id: str, period: date, kind: str, ppa: PPA, provisional: bool):
    return {
        "id": stable_uuid("settlement", dataset_id, period, kind, line.kind),
        "dataset_id": dataset_id,
        "plant_id": plant_id,
        "period_start": period,
        "period_kind": kind,
        "kind": line.kind,
        "qty_kwh": line.qty_kwh.quantize(Decimal("0.1")),
        "rate_inr_per_kwh": line.rate.quantize(Decimal("0.0001")),
        "amount_inr": line.amount,
        "contract_id": ppa.id,
        "clause_ref": line.clause_ref,
        "inputs": line.inputs,
        "provisional": provisional,
    }


def run(conn: Connection, dataset_id: str) -> list[dict]:
    ppa = load_ppa()
    register(conn, ppa, "ppa")
    ledger = read_ledger(conn, dataset_id)
    if ledger.empty:
        raise ValueError(f"no accounting ledger for {dataset_id}; run the accounting step first")
    plant_id = ledger["plant_id"].iloc[0]
    rows = build_lines(ledger, ppa, dataset_id, plant_id)
    replace_rows(conn, "settlement_line", {"dataset_id": dataset_id}, pd.DataFrame(rows))
    return rows


def total(conn: Connection, dataset_id: str, period_month: date) -> Decimal:
    """revenue_settled_inr for a month: monthly lines (+ annual true-up lines booked in December)."""
    q = text(
        "SELECT coalesce(sum(amount_inr), 0) FROM settlement_line WHERE dataset_id = :d AND "
        "((period_kind = 'month' AND period_start = :m) OR "
        "(period_kind = 'year' AND :m = make_date(extract(year FROM period_start)::int, 12, 1)))"
    )
    return Decimal(conn.execute(q, {"d": dataset_id, "m": period_month}).scalar_one())
