"""T-SET-01: docs/02 §6.4 worked examples to the paisa. T-SET-02: excess/shortfall exclusive; interpretation A."""

import dataclasses
from decimal import Decimal

import pytest

from app.contracts.loader import load_ppa
from app.settlement import clauses

D = Decimal


@pytest.fixture
def ppa():
    # The worked examples use the illustrative 24.0 % CUF; the live contract carries the approved-baseline value.
    return dataclasses.replace(load_ppa(), declared_cuf=D("0.240"))


def test_shortfall_example(ppa):
    lines, test = clauses.annual_lines(D("92000000"), D("4000"), D("8760"), D("0"), D("0"), ppa)
    assert test.declared_kwh == D("105120000.000")
    assert test.min_kwh == D("94608000.00000")
    shortfall = next(x for x in lines if x.kind == "shortfall_comp")
    assert shortfall.qty_kwh == D("2608000.00000")
    assert shortfall.amount == D("-1630000.00")  # ₹16.30 lakh payable by the generator
    assert shortfall.clause_ref == "C4.3"


def test_backdown_example(ppa):
    line = clauses.backdown_comp(D("8000000"), D("340"), D("40"), ppa)
    deemed = D(line.inputs["deemed_kwh"])
    assert round(deemed) == 941176
    assert line.amount == D("1176470.59")  # ₹11.76 lakh
    assert line.clause_ref == "C4.4"


def test_grid_below_threshold_pays_nothing_but_relaxes(ppa):
    lines, test = clauses.annual_lines(D("94000000"), D("4000"), D("8760"), D("0"), D("14"), ppa)
    grid = next(x for x in lines if x.kind == "grid_unavail_comp")
    assert grid.amount == D("0.00")
    assert test.deemed_grid_kwh == D("94000000") / D("4000") * D("14")
    assert test.relaxed_min_kwh == test.min_kwh - test.deemed_grid_kwh


def test_energy_charge(ppa):
    assert clauses.energy_charge(D("8540000"), ppa).amount == D("21350000.00")


# ---- T-SET-02
@pytest.mark.parametrize("accountable", ["80000000", "100000000", "120000000", "140000000"])
def test_excess_and_shortfall_mutually_exclusive(ppa, accountable):
    lines, _ = clauses.annual_lines(D(accountable), D("4000"), D("8760"), D("0"), D("0"), ppa)
    amounts = {x.kind: x.amount for x in lines}
    assert amounts["excess_repricing"] == 0 or amounts["shortfall_comp"] == 0


def test_excess_repriced_at_25_percent_discount(ppa):
    lines, test = clauses.annual_lines(D("120000000"), D("4000"), D("8760"), D("0"), D("0"), ppa)
    excess = next(x for x in lines if x.kind == "excess_repricing")
    assert test.excess_kwh == D("120000000") - D("1.10") * D("105120000")
    assert excess.amount == -(test.excess_kwh * D("2.50") * D("0.25")).quantize(D("0.01"))


def test_relaxation_uses_deemed_kwh_interpretation_a(ppa):
    no_relief, _ = clauses.annual_lines(D("94000000"), D("4000"), D("8760"), D("0"), D("0"), ppa)
    relief, test = clauses.annual_lines(D("94000000"), D("4000"), D("8760"), D("941176"), D("0"), ppa)
    short = {x.kind: x.amount for x in no_relief}["shortfall_comp"]
    assert short < 0
    assert {x.kind: x.amount for x in relief}["shortfall_comp"] == D("0.00")
    assert test.relaxed_min_kwh == test.min_kwh - D("941176")
    # Interpretation A: deemed kWh never become accountable energy
    assert D(relief[0].inputs["accountable_kwh"]) == D("94000000")
