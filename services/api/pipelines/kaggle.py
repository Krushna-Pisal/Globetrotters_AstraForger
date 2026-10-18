"""`make ingest-kaggle`: M1 real slice (docs/06 §4). Dataset kaggle_p2_2020, plant KGL-P2, source_kind measured.

ingest + quality flags -> actual_output -> real-data expected model (k_i fit, holdout) -> peer detection
-> calibration of scenario texture -> data/processed/kaggle_p2_2020/quality_report.json
"""

import json
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import Connection, text

from app.core.bulk import copy_frame, replace_rows, stable_uuid, upsert_dataset, write_measurements
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.lineage import sha256_hash
from app.detection import peer
from app.ingest import kaggle
from app.ingest.manifest import register_batch, sha256_file, write_manifest
from app.performance import realdata
from app.quality import flags, score, validated
from app.twin.loader import load_plant, plant_config_path, sync_twin

DATASET_ID = "kaggle_p2_2020"
PLANT_ID = "KGL-P2"
SOURCE_URL = "https://www.kaggle.com/datasets/anikannal/solar-power-generation-data"
LICENSE = "unverified - see the Kaggle dataset page (docs/00 human check)"
FILES = [
    "Plant_1_Generation_Data.csv",
    "Plant_1_Weather_Sensor_Data.csv",
    "Plant_2_Generation_Data.csv",
    "Plant_2_Weather_Sensor_Data.csv",
]


def raw_dir() -> Path:
    return get_settings().data_dir / "raw" / "kaggle"


def plant1_check(directory: Path) -> dict:
    """Plant 1 is not ingested; its DC channel is checked and reported (D04)."""
    gen = kaggle.parse_file(directory / "Plant_1_Generation_Data.csv")
    ratio = kaggle.ac_dc_ratio(gen)
    ws = kaggle.parse_file(directory / "Plant_1_Weather_Sensor_Data.csv")
    return {
        "ac_dc_ratio": round(ratio, 4),
        "dc_usable": kaggle.dc_usable(ratio),
        "irradiance_unit": kaggle.irradiance_unit(ws["IRRADIATION"])[0],
        "ingested": False,
        "reason": "DC_POWER ~10x AC_POWER; Plant 2 is the real slice (D04)",
    }


def ingest(conn: Connection, directory: Path) -> dict:
    plant = load_plant(PLANT_ID)
    hashes = {name: sha256_file(directory / name) for name in FILES if (directory / name).exists()}
    missing = [n for n in FILES if n not in hashes]
    if missing:
        raise FileNotFoundError(f"missing Kaggle files in {directory}: {missing}")
    write_manifest(
        DATASET_ID,
        {
            "dataset_id": DATASET_ID,
            "source": SOURCE_URL,
            "license": LICENSE,
            "files": {n: {"sha256": h, "bytes": (directory / n).stat().st_size} for n, h in hashes.items()},
            "date_formats": kaggle.DATE_FORMATS,
            "timezone_assumed": "Asia/Kolkata",
        },
    )

    gen = kaggle.parse_file(directory / "Plant_2_Generation_Data.csv")
    ws_raw = kaggle.parse_file(directory / "Plant_2_Weather_Sensor_Data.csv")
    ratio = kaggle.ac_dc_ratio(gen)
    irr_unit, _ = kaggle.irradiance_unit(ws_raw["IRRADIATION"])

    upsert_dataset(
        conn,
        DATASET_ID,
        PLANT_ID,
        "measured",
        {"source": SOURCE_URL, "files": hashes, "plant_config_sha256": sha256_file(plant_config_path(PLANT_ID))},
        seed=None,
    )
    assets = sync_twin(conn, PLANT_ID)
    key_to_asset = {a.attrs["source_key"]: a.id for a in assets if "source_key" in a.attrs}
    ws_asset = next(a.id for a in assets if a.kind == "weather_station")
    inverters = [a.id for a in assets if a.kind == "inverter"]

    gen_batch = register_batch(
        conn,
        DATASET_ID,
        "kaggle:Plant_2_Generation_Data.csv",
        hashes["Plant_2_Generation_Data.csv"],
        "measured",
        SOURCE_URL,
        LICENSE,
    )
    ws_batch = register_batch(
        conn,
        DATASET_ID,
        "kaggle:Plant_2_Weather_Sensor_Data.csv",
        hashes["Plant_2_Weather_Sensor_Data.csv"],
        "measured",
        SOURCE_URL,
        LICENSE,
        notes="IRRADIATION stored as poa_wm2 (x1000 from kW/m2); used as POA in real-data mode",
    )
    g = kaggle.generation_measurements(gen, key_to_asset, include_dc=kaggle.dc_usable(ratio))
    g["batch_id"] = gen_batch
    w = kaggle.weather_measurements(ws_raw, ws_asset)
    w["batch_id"] = ws_batch
    meas = pd.concat([g, w], ignore_index=True)
    rated = float(plant["inverter"]["rated_ac_kw_inferred"])
    meas["quality"] = flags.flag_measurements(meas, rated)
    meas["dataset_id"] = DATASET_ID
    meas["interval_s"] = 900
    meas["value_text"] = None
    meas["source_kind"] = "measured"
    cols = [
        "dataset_id",
        "asset_id",
        "quantity",
        "ts_start",
        "interval_s",
        "value",
        "value_text",
        "unit",
        "quality",
        "source_kind",
        "batch_id",
    ]
    n_meas = write_measurements(conn, DATASET_ID, meas[cols])

    index = kaggle.full_index(gen)
    actual = validated.energy_actual(meas, inverters, index, DATASET_ID)
    replace_rows(conn, "actual_output", {"dataset_id": DATASET_ID}, actual)

    ws = _ws_frame(meas, ws_asset)
    gamma = float(plant["module"]["gamma_pdc_per_c"])
    model = realdata.fit(actual, ws, gamma, rated, int(plant["model"]["calibration_days"]))
    exp = realdata.expected(model, actual, ws, gamma)
    inputs_hash = sha256_hash(
        {
            "weather_batch": str(ws_batch),
            "plant_config": sha256_file(plant_config_path(PLANT_ID)),
            "model_version": realdata.MODEL_VERSION,
            "k": model.k,
        }
    )
    exp_rows = pd.DataFrame(
        {
            "dataset_id": DATASET_ID,
            "asset_id": exp["asset_id"],
            "ts_start": exp["ts_start"],
            "interval_s": 900,
            "poa_wm2": exp["poa"],
            "t_cell_c": exp["t_cell_c"],
            "e_potential_kwh": exp["e_potential_kwh"],
            "band_rel": model.band_rel,
            "clipped": exp["clipped"],
            "model_version": realdata.MODEL_VERSION,
            "inputs_hash": inputs_hash,
        }
    )
    replace_rows(conn, "expected_output", {"dataset_id": DATASET_ID, "model_version": realdata.MODEL_VERSION}, exp_rows)

    ws_series = ws.set_index("ts_start")
    dq = score.daily_score(index, ws_series["poa"], ws_series["ok"], actual)
    daylight = score.daylight_mask(index, ws_series["poa"], actual)
    ratios = peer.daily_peer_ratio(actual, daylight)
    peer_events = peer.detect(ratios)
    _write_peer_events(conn, peer_events)

    texture = calibrate_texture(model)
    return {
        "dataset_id": DATASET_ID,
        "rows": {"measurement": n_meas, "actual_output": len(actual), "expected_output": len(exp_rows)},
        "period_utc": [str(index[0]), str(index[-1])],
        "inverters": len(inverters),
        "irradiance_unit_detected": irr_unit,
        "ac_dc_ratio": round(ratio, 4),
        "dc_usable": kaggle.dc_usable(ratio),
        "duplicates_dropped": {"generation": kaggle.duplicate_count(gen), "weather": kaggle.duplicate_count(ws_raw)},
        "gaps": kaggle.gap_report(gen),
        "weather_gaps": kaggle.gap_report(ws_raw),
        "daily_yield_check": kaggle.daily_yield_check(gen),
        "quality_flags": flags.summarize(meas["quality"], meas),
        "data_quality_score": {
            "mean": round(float(dq["score"].mean()), 4),
            "min": round(float(dq["score"].min()), 4),
            "daily": {str(r.date): round(float(r.score), 4) for r in dq.itertuples()},
        },
        "model": {
            "version": realdata.MODEL_VERSION,
            "rated_ac_kw_inferred": rated,
            "calibration_days": [str(d) for d in model.calibration_days],
            "k_by_inverter": {a: round(v, 2) for a, v in model.k.items()},
            "sigma_rel": round(model.sigma_rel, 4),
            "band_rel_95": round(model.band_rel, 4),
            "holdout": realdata.holdout_error(model, exp),
            "assumption": "plant irradiance sensor used as POA; k_i fitted against AC power (D19)",
        },
        "detection": {
            "rule": "peer_deviation (daily ratio < 0.95 for >= 3 days)",
            "suspected": peer_events,
            "peer_ratio_mean_by_inverter": ratios.mean().round(4).to_dict(),
        },
        "calibrated_texture": texture,
        "not_applicable": {
            "heartbeat": "no heartbeat channel; gaps detected from missing intervals only",
            "status_codes": "no status channel",
            "meter_reconciliation": "no delivery-point meter",
        },
    }


def _ws_frame(meas: pd.DataFrame, ws_asset: str) -> pd.DataFrame:
    w = meas[meas["asset_id"] == ws_asset].pivot(index="ts_start", columns="quantity", values="value")
    q = meas[meas["asset_id"] == ws_asset].pivot(index="ts_start", columns="quantity", values="quality")
    ok = (q["poa_wm2"] == "ok") & (q["t_mod_c"] == "ok")
    return pd.DataFrame(
        {"ts_start": w.index, "poa": w["poa_wm2"].to_numpy(), "t_mod": w["t_mod_c"].to_numpy(), "ok": ok.to_numpy()}
    )


def _write_peer_events(conn: Connection, events: list[dict]) -> None:
    conn.execute(text("DELETE FROM event WHERE dataset_id = :d"), {"d": DATASET_ID})
    rows = []
    for e in events:
        start = pd.Timestamp(e["first_day"]).tz_localize("Asia/Kolkata").tz_convert("UTC")
        end = (pd.Timestamp(e["last_day"]) + pd.Timedelta(days=1)).tz_localize("Asia/Kolkata").tz_convert("UTC")
        rows.append(
            {
                "id": stable_uuid("event", DATASET_ID, e["asset_id"], "peer", start),
                "dataset_id": DATASET_ID,
                "asset_id": e["asset_id"],
                "category": "underperformance",
                "cause_code": "PEER_DEVIATION",
                "start_ts": start,
                "end_ts": end,
                "controllable": True,
                "confidence": "suspected",
                "evidence": {"rules": ["peer_deviation"], "metrics": {k: str(v) for k, v in e.items()}},
                "setpoint_kw": None,
                "source_kind": "derived",
            }
        )
    if rows:
        copy_frame(conn, "event", pd.DataFrame(rows))


def calibrate_texture(model: realdata.RealModel) -> dict:
    """docs/06 §4 step 5. Spread uses a robust MAD estimate so real underperformers do not inflate it (D20)."""
    k = pd.Series(model.k)
    rel = k / k.median()
    spread = float(1.4826 * (rel - rel.median()).abs().median())
    return {
        "interval_noise_sigma": round(model.sigma_rel, 4),
        "inverter_efficiency_spread_sigma": round(spread, 4),
        "inverter_efficiency_spread_sigma_plain_std": round(float(rel.std(ddof=1)), 4),
    }


def write_texture_to_scenario(texture: dict) -> Path:
    path = get_settings().configs_dir / "scenarios" / "thar1_demo_2024.yaml"
    body = path.read_text(encoding="utf-8")
    body = re.sub(
        r"(interval_noise_sigma: )[0-9.]+(\s*#.*)?",
        rf"\g<1>{texture['interval_noise_sigma']}   # calibrated on kaggle_p2_2020 (M1): pooled sigma_rel",
        body,
    )
    body = re.sub(
        r"(inverter_efficiency_spread_sigma: )[0-9.]+(\s*#.*)?",
        rf"\g<1>{texture['inverter_efficiency_spread_sigma']}   # calibrated on kaggle_p2_2020 (M1): "
        "robust std of k_i / median k (D20)",
        body,
    )
    body = body.replace(
        "# calibrated on Kaggle Plant 2 (docs/06 §4); replace with fitted values",
        "# calibrated on Kaggle Plant 2 (docs/06 §4) by make ingest-kaggle",
    )
    path.write_text(body, encoding="utf-8")
    return path


def run(_args=None) -> None:
    directory = raw_dir()
    with get_engine().begin() as conn:
        report = ingest(conn, directory)
    report["plant_1"] = plant1_check(directory)
    write_texture_to_scenario(report["calibrated_texture"])
    out = get_settings().data_dir / "processed" / DATASET_ID / "quality_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "rows",
                    "inverters",
                    "irradiance_unit_detected",
                    "ac_dc_ratio",
                    "data_quality_score",
                    "calibrated_texture",
                )
            },
            default=str,
        )[:2000]
    )
    print("model:", {k: report["model"][k] for k in ("sigma_rel", "band_rel_95", "holdout")})
    print("suspected:", report["detection"]["suspected"])
    print(f"report: {out}")
