"""INR money helpers. Decimal only; quantize each line to paise with ROUND_HALF_UP, then sum lines (docs/02 §6.5)."""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

PAISE = Decimal("0.01")


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Convert to Decimal. Floats are rejected: they cannot represent INR amounts exactly."""
    if isinstance(value, float):
        raise TypeError("float is not allowed for INR; pass Decimal, int or str")
    if isinstance(value, bool):
        raise TypeError("bool is not a money value")
    return value if isinstance(value, Decimal) else Decimal(value)


def quantize_inr(value: Decimal | int | str) -> Decimal:
    return to_decimal(value).quantize(PAISE, rounding=ROUND_HALF_UP)


def sum_lines(lines: Iterable[Decimal]) -> Decimal:
    """Total of already-quantized lines. Each line must already be at paise precision."""
    total = Decimal("0.00")
    for line in lines:
        line = to_decimal(line)
        if line != line.quantize(PAISE):
            raise ValueError(f"line {line} is not quantized to paise; quantize per line before summing")
        total += line
    return total
