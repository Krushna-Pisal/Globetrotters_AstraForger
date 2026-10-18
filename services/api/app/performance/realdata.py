"""Real-data mode expected output (docs/02 §3.1, §3.4) for plants without orientation metadata (Kaggle Plant 2).

    p_ac_expected = k_i × G × [1 + γ (T_mod − 25)] / 1000, clipped at the (inferred) rated AC

The measured irradiance is used as plane-of-array (labelled assumption). k_i is fitted per inverter against AC power
directly (D19: the dataset's DC channel is not needed and k_i absorbs inverter efficiency) on healthy intervals of the
first 7 clean days, then evaluated on the remaining days (holdout).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.timeutil import INTERVAL_H, local_date

MODEL_VERSION = "perf-real-1.0"
FIT_MIN_IRR = 200.0  # W/m²: fit and σ only where the sensor is well above noise
CLIP_FRACTION = 0.97
CLEAN_COVERAGE = 0.95
HEALTHY_BAND = 0.15  # healthy = producing and within ±15 % of the fleet median at that interval (D19)


@dataclass
class RealModel:
    k: dict[str, float]
    sigma_rel: float
    calibration_days: list
    holdout_days: list
    rated_ac_kw: float

    @property
    def band_rel(self) -> float:
        return 1.96 * self.sigma_rel


def base_term(poa: pd.Series, t_mod: pd.Series, gamma: float) -> pd.Series:
    return poa / 1000.0 * (1.0 + gamma * (t_mod - 25.0))


def clean_days(actual: pd.DataFrame, ws: pd.DataFrame, n_inverters: int) -> list:
    """Days where every inverter and the weather station have ≥ 95 % of daylight intervals ok (default #5)."""
    w = ws.copy()
    w["date"] = local_date(w["ts_start"]).to_numpy()
    day_ts = w.loc[w["poa"] > 0, ["ts_start", "date"]]
    ws_cov = w[(w["poa"] > 0) & w["ok"]].groupby("date").size() / day_ts.groupby("date").size()
    a = actual.merge(day_ts, on="ts_start")
    inv_cov = a[a["quality"] == "ok"].groupby(["date", "asset_id"]).size().unstack()
    inv_cov = inv_cov.div(day_ts.groupby("date").size(), axis=0)
    good = inv_cov.reindex(columns=sorted(actual["asset_id"].unique())).fillna(0)
    ok_days = good.index[(good.min(axis=1) >= CLEAN_COVERAGE) & (good.notna().sum(axis=1) == n_inverters)]
    return sorted(d for d in ok_days if ws_cov.get(d, 0) >= CLEAN_COVERAGE)


def fit(actual: pd.DataFrame, ws: pd.DataFrame, gamma: float, rated_ac_kw: float, n_days: int) -> RealModel:
    """actual: actual_output rows; ws: ts_start, poa, t_mod, ok."""
    inverters = sorted(actual["asset_id"].unique())
    days = clean_days(actual, ws, len(inverters))
    if len(days) < n_days + 1:
        raise ValueError(f"only {len(days)} clean days; need {n_days} for calibration plus a holdout")
    calib = days[:n_days]
    all_days = sorted(set(local_date(ws["ts_start"])))
    holdout = [d for d in all_days if d > calib[-1]]

    frame = _join(actual, ws, gamma)
    in_calib = frame["date"].isin(calib) & (frame["poa"] >= FIT_MIN_IRR) & (frame["quality"] == "ok")
    unclipped = frame["p_kw"] < CLIP_FRACTION * rated_ac_kw
    sel = frame[in_calib & unclipped & frame["ws_ok"].fillna(False).astype(bool)]
    sel = sel[healthy(sel)]
    k = (sel.groupby("asset_id")["p_kw"].sum() / sel.groupby("asset_id")["base"].sum()).to_dict()

    pred = sel["base"] * sel["asset_id"].map(k)
    ratio = sel["p_kw"] / pred
    sigma = float(ratio.std(ddof=1))
    return RealModel(k=k, sigma_rel=sigma, calibration_days=calib, holdout_days=holdout, rated_ac_kw=rated_ac_kw)


def healthy(frame: pd.DataFrame) -> pd.Series:
    """Peer-consistent intervals: real outages and underperformance stay out of the fit and of sigma_rel."""
    fleet = frame.groupby("ts_start")["p_kw"].transform("median")
    rel = frame["p_kw"] / fleet
    return (frame["p_kw"] > 0) & (rel - 1).abs().le(HEALTHY_BAND)


def _join(actual: pd.DataFrame, ws: pd.DataFrame, gamma: float) -> pd.DataFrame:
    f = actual.merge(ws.rename(columns={"ok": "ws_ok"}), on="ts_start", how="left")
    f["base"] = base_term(f["poa"], f["t_mod"], gamma)
    f["p_kw"] = f["e_kwh"] / INTERVAL_H
    f["date"] = local_date(f["ts_start"]).to_numpy()
    return f


def expected(model: RealModel, actual: pd.DataFrame, ws: pd.DataFrame, gamma: float) -> pd.DataFrame:
    """E_potential per inverter-interval wherever the weather station reported."""
    f = _join(actual[["asset_id", "ts_start", "e_kwh", "quality"]], ws, gamma)
    f = f[f["poa"].notna() & f["t_mod"].notna()].copy()
    raw = (f["base"] * f["asset_id"].map(model.k)).clip(lower=0)
    f["clipped"] = raw >= model.rated_ac_kw
    f["e_potential_kwh"] = np.minimum(raw, model.rated_ac_kw) * INTERVAL_H
    f["t_cell_c"] = f["t_mod"]
    return f


def holdout_error(model: RealModel, exp: pd.DataFrame) -> dict:
    h = exp[exp["date"].isin(model.holdout_days) & (exp["quality"] == "ok")]
    daily = h.groupby(["asset_id", "date"])[["e_kwh", "e_potential_kwh"]].sum()
    daily = daily[daily["e_potential_kwh"] > 0]
    ape = (daily["e_kwh"] - daily["e_potential_kwh"]).abs() / daily["e_potential_kwh"]
    day_iv = h[h["poa"] >= FIT_MIN_IRR]
    nrmse = float(
        np.sqrt(((day_iv["e_kwh"] - day_iv["e_potential_kwh"]) ** 2).mean()) / day_iv["e_potential_kwh"].mean()
    )
    per_inv = ape.groupby(level="asset_id").median().round(4).to_dict()
    return {
        "holdout_days": len(model.holdout_days),
        "daily_energy_mape": round(float(ape.mean()), 4),
        "daily_energy_median_ape": round(float(ape.median()), 4),
        "interval_nrmse_poa_ge_200": round(nrmse, 4),
        "median_ape_by_inverter": per_inv,
        "note": "holdout error includes real underperformance and outages, not only model error",
    }
