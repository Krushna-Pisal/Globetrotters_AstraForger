"""CFADS and DSCR (docs/02 §9).

CFADS_month = revenue_settled_month + om_ld_received − opex/12 − tax/12 − maintenance_capex/12
(working capital and reserve movements = 0 in MVP). Not EBITDA: it is after tax and capex.
DSCR_YTD = Σ CFADS / Σ debt service, provisional until the year is complete. O&M LDs are booked in December.
"""

from decimal import Decimal

from app.core.money import quantize_inr

DSCR_PLACES = Decimal("0.0001")


def split_annual(annual: Decimal, months: int = 12) -> list[Decimal]:
    """Monthly equal instalments quantized to paise; the last month absorbs the rounding."""
    each = quantize_inr(annual / months)
    return [each] * (months - 1) + [quantize_inr(annual - each * (months - 1))]


def cfads(revenue: Decimal, om_ld: Decimal, opex: Decimal, tax: Decimal, capex: Decimal) -> Decimal:
    return quantize_inr(revenue + om_ld - opex - tax - capex)


def dscr(cfads_sum: Decimal, debt_sum: Decimal) -> Decimal | None:
    return (cfads_sum / debt_sum).quantize(DSCR_PLACES) if debt_sum else None
