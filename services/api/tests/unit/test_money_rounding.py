"""T-SET-05 (foundation): Decimal only; quantize per line with ROUND_HALF_UP; totals = sum of quantized lines."""

from decimal import Decimal

import pytest

from app.core.money import quantize_inr, sum_lines, to_decimal


def test_round_half_up_to_paise():
    assert quantize_inr("2.345") == Decimal("2.35")
    assert quantize_inr("2.344") == Decimal("2.34")
    assert quantize_inr("-2.345") == Decimal("-2.35")


def test_float_rejected():
    with pytest.raises(TypeError):
        to_decimal(2.5)
    with pytest.raises(TypeError):
        quantize_inr(0.1)


def test_total_is_sum_of_quantized_lines():
    # Three lines of ₹0.005 each: per-line rounding gives 0.03; rounding the raw sum would give 0.02.
    lines = [quantize_inr("0.005")] * 3
    assert sum_lines(lines) == Decimal("0.03")


def test_unquantized_line_rejected():
    with pytest.raises(ValueError):
        sum_lines([Decimal("1.005")])


def test_shortfall_example_arithmetic_in_decimal():
    # docs/02 §6.4: 2,608,000 kWh × ₹2.50 × 0.25 = ₹16.30 lakh
    assert quantize_inr(Decimal("2608000") * Decimal("2.50") * Decimal("0.25")) == Decimal("1630000.00")
