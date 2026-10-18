"""PPA clause arithmetic (docs/02 §6). Pure Decimal functions; one quantized line per clause (§6.5).

Reads only the ledger values and the PPA. Never the baseline (invariant 2), never O&M LDs (invariant 3).
Interpretation A (§6.6): deemed kWh relax the minimum-energy test and are NOT added to accountable energy.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.contracts.loader import PPA
from app.core.money import quantize_inr

ZERO = Decimal("0")


@dataclass(frozen=True)
class Line:
    kind: str
    clause_ref: str
    qty_kwh: Decimal
    rate: Decimal
    amount: Decimal
    inputs: dict = field(default_factory=dict)


def dec(x) -> Decimal:
    """float kWh/h -> Decimal via its shortest repr (no binary noise beyond the float's own value)."""
    return x if isinstance(x, Decimal) else Decimal(repr(float(x)))


def avg_gen_per_hour(accountable_kwh: Decimal, hours_with_generation: Decimal) -> Decimal:
    return accountable_kwh / hours_with_generation if hours_with_generation > 0 else ZERO


def energy_charge(accountable_kwh: Decimal, ppa: PPA) -> Line:
    return Line(
        "energy_charge",
        "C4.1",
        accountable_kwh,
        ppa.tariff,
        quantize_inr(accountable_kwh * ppa.tariff),
        {"accountable_kwh": str(accountable_kwh), "tariff": str(ppa.tariff)},
    )


def backdown_comp(accountable_kwh: Decimal, hours_with_generation: Decimal, backdown_hours: Decimal, ppa: PPA) -> Line:
    avg = avg_gen_per_hour(accountable_kwh, hours_with_generation)
    deemed = avg * backdown_hours
    paid_kwh = ppa.backdown_fraction * deemed
    return Line(
        "backdown_comp",
        "C4.4",
        paid_kwh,
        ppa.tariff,
        quantize_inr(paid_kwh * ppa.tariff),
        {
            "avg_gen_per_hour": str(avg),
            "backdown_hours": str(backdown_hours),
            "deemed_kwh": str(deemed),
            "fraction": str(ppa.backdown_fraction),
        },
    )


@dataclass(frozen=True)
class AnnualTest:
    declared_kwh: Decimal
    max_kwh: Decimal
    min_kwh: Decimal
    relaxed_min_kwh: Decimal
    excess_kwh: Decimal
    shortfall_kwh: Decimal
    deemed_backdown_kwh: Decimal
    deemed_grid_kwh: Decimal


def annual_test(
    accountable_kwh: Decimal, hours_in_year: Decimal, deemed_backdown_kwh: Decimal, deemed_grid_kwh: Decimal, ppa: PPA
) -> AnnualTest:
    declared = ppa.declared_cuf * ppa.contracted_kw * hours_in_year
    mx = ppa.max_fraction * declared
    mn = ppa.min_fraction * declared
    relaxed = mn - deemed_backdown_kwh - deemed_grid_kwh
    excess = max(ZERO, accountable_kwh - mx)
    shortfall = max(ZERO, relaxed - accountable_kwh)
    return AnnualTest(declared, mx, mn, relaxed, excess, shortfall, deemed_backdown_kwh, deemed_grid_kwh)


def annual_lines(
    accountable_kwh: Decimal,
    hours_with_generation: Decimal,
    hours_in_year: Decimal,
    deemed_backdown_kwh: Decimal,
    grid_hours_counted: Decimal,
    ppa: PPA,
) -> tuple[list[Line], AnnualTest]:
    avg = avg_gen_per_hour(accountable_kwh, hours_with_generation)
    deemed_grid = avg * grid_hours_counted
    test = annual_test(accountable_kwh, hours_in_year, deemed_backdown_kwh, deemed_grid, ppa)
    common = {
        "declared_kwh": str(test.declared_kwh),
        "max_kwh": str(test.max_kwh),
        "min_kwh": str(test.min_kwh),
        "relaxed_min_kwh": str(test.relaxed_min_kwh),
        "accountable_kwh": str(accountable_kwh),
        "hours_in_year": str(hours_in_year),
        "interpretation": ppa.interpretation,
    }
    excess_rate = ppa.tariff * (1 - ppa.excess_rate_fraction)
    shortfall_rate = ppa.tariff * ppa.shortfall_rate_fraction
    paid_grid_h = max(ZERO, grid_hours_counted - ppa.grid_threshold_h)
    grid_kwh = avg * paid_grid_h
    grid_rate = ppa.tariff * ppa.grid_rate_fraction
    lines = [
        Line(
            "excess_repricing",
            "C4.2",
            test.excess_kwh,
            excess_rate,
            -quantize_inr(test.excess_kwh * excess_rate),
            common | {"excess_kwh": str(test.excess_kwh)},
        ),
        Line(
            "grid_unavail_comp",
            "C4.5",
            grid_kwh,
            grid_rate,
            quantize_inr(grid_kwh * grid_rate),
            common
            | {
                "avg_gen_per_hour_year": str(avg),
                "counted_hours": str(grid_hours_counted),
                "threshold_h": str(ppa.grid_threshold_h),
                "paid_hours": str(paid_grid_h),
                "deemed_grid_kwh": str(deemed_grid),
            },
        ),
        Line(
            "shortfall_comp",
            "C4.3",
            test.shortfall_kwh,
            shortfall_rate,
            -quantize_inr(test.shortfall_kwh * shortfall_rate),
            common
            | {
                "shortfall_kwh": str(test.shortfall_kwh),
                "deemed_backdown_kwh": str(deemed_backdown_kwh),
                "deemed_grid_kwh": str(deemed_grid),
            },
        ),
    ]
    return lines, test
