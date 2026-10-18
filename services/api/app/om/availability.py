"""Energy-based availability A_E and O&M liquidated damages (docs/02 §4.3–4.4). O&M contract only (invariant 3).

A_E = 1 − L_outage_eligible / E_potential_eligible. Intervals with an excluded cause (grid unavailability,
curtailment, force majeure, owner instructed, no_data) are removed from both terms.
LD_kWh = max(0, guarantee − A_E,annual) × E_potential_eligible,annual; LD_INR = min(LD_kWh × rate, cap).
Judged against expected output, never the baseline (invariant 11).
"""

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from app.contracts.loader import OM
from app.core.money import quantize_inr

CATEGORY_TO_CAUSE = {"grid_unavailability": "grid_unavailability", "curtailment": "curtailment"}


def interval_frame(expected: pd.DataFrame, actual: pd.DataFrame, events: pd.DataFrame, om: OM) -> pd.DataFrame:
    """One row per inverter-interval with ep, actual, outage flag and excluded flag."""
    f = expected[["asset_id", "ts_start", "e_potential_kwh"]].merge(
        actual[["asset_id", "ts_start", "e_kwh", "quality"]], on=["asset_id", "ts_start"], how="left"
    )
    f["excluded"] = f["quality"].isna() | (f["quality"] == "no_data")
    f["outage"] = False
    plant_level = events["asset_id"].map(lambda a: "/" not in a)
    for e in events.itertuples():
        end = e.end_ts if pd.notna(e.end_ts) else f["ts_start"].max() + pd.Timedelta(minutes=15)
        in_t = (f["ts_start"] >= e.start_ts) & (f["ts_start"] < end)
        cause = CATEGORY_TO_CAUSE.get(e.category, e.cause_code.lower())
        if cause in om.excluded_causes:
            mask = in_t if plant_level.loc[e.Index] else in_t & (f["asset_id"] == e.asset_id)
            f.loc[mask, "excluded"] = True
        elif e.category == "equipment_outage":
            f.loc[in_t & (f["asset_id"] == e.asset_id), "outage"] = True
    return f


def energy_based(f: pd.DataFrame) -> tuple[float, float, float]:
    """Returns (A_E, L_outage_eligible_kWh, E_potential_eligible_kWh) for the rows given."""
    el = f[~f["excluded"]]
    gap = (el["e_potential_kwh"] - el["e_kwh"].fillna(0.0)).clip(lower=0.0)
    loss = float(gap[el["outage"]].sum())
    ep = float(el["e_potential_kwh"].sum())
    return (1.0 - loss / ep if ep else 1.0), loss, ep


@dataclass(frozen=True)
class LD:
    availability: Decimal
    ld_kwh: Decimal
    amount: Decimal
    capped: bool
    inputs: dict


def liquidated_damages(a_e: Decimal, ep_eligible_kwh: Decimal, om: OM) -> LD:
    shortfall = max(Decimal("0"), om.guarantee - a_e)
    ld_kwh = shortfall * ep_eligible_kwh
    raw = quantize_inr(ld_kwh * om.ld_rate)
    cap = quantize_inr(om.ld_cap)
    amount = min(raw, cap)
    return LD(
        a_e,
        ld_kwh,
        amount,
        raw > cap,
        {
            "guarantee": str(om.guarantee),
            "a_e": str(a_e),
            "ep_eligible_kwh": str(ep_eligible_kwh),
            "rate": str(om.ld_rate),
            "uncapped_inr": str(raw),
            "cap_inr": str(cap),
        },
    )
