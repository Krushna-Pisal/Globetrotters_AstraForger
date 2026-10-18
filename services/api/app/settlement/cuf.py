"""cuf_actual = accountable_kWh / (contracted AC kW × hours in period) (docs/02 §6.2)."""

from decimal import Decimal

from app.contracts.loader import PPA


def actual(accountable_kwh: Decimal, hours_in_period: Decimal, ppa: PPA) -> Decimal:
    return accountable_kwh / (ppa.contracted_kw * hours_in_period)
