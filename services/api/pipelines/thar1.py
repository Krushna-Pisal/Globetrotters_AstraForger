"""THAR1 synthetic year: fetch-weather, scenario, and the pipeline steps quality -> expected -> detect (M2)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sqlalchemy import Connection, text

from app.core.bulk import copy_frame, replace_rows, stable_uuid, upsert_dataset, write_measurements
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.lineage import sha256_hash
from app.core.timeutil import INTERVAL_H, PLANT_TZ, interval_index
from app.detection import peer, status
from app.ingest import weather
from app.ingest.manifest import register_batch, sha256_file
from app.performance import model, realdata, weather15
from app.quality import flags, validated
from app.twin.loader import build_assets, load_plant, plant_config_path, sync_twin

PLANT_ID = "THAR1"


def scenario_path(dataset_id: str) -> Path:
    return get_settings().configs_dir / "scenarios" / f"{dataset_id}.yaml"


def load_scenario(dataset_id: str) -> dict:
    return yaml.safe_load(scenario_path(dataset_id).read_text(encoding="utf-8"))["scenario"]


def open_meteo_cache(scn: dict) -> Path:
    return get_settings().configs_dir.parent / scn["weather"]["cache"]


def pvgis_cache() -> Path:
    return weather.weather_dir() / "thar1_pvgis_tmy.json"


# ---------------------------------------------------------------- fetch-weather (the only internet step)
def fetch_weather(_args=None, dataset_id: str = "thar1_demo_2024") -> None:
    scn = load_scenario(dataset_id)
    plant = load_plant(PLANT_ID)
    lat, lon = plant["location"]["lat"], plant["location"]["lon"]
    start = (pd.Timestamp(scn["period"]["start"]).tz_convert("UTC") - pd.Timedelta(days=1)).date().isoformat()
    end = pd.Timestamp(scn["period"]["end"]).tz_convert("UTC").date().isoformat()
    om = open_meteo_cache(scn)
    om.parent.mkdir(parents=True, exist_ok=True)
    if om.exists():
        print(f"cached: {om}")
    else:
        try:
            weather.fetch_open_meteo(lat, lon, start, end, om)
            print(f"fetched Open-Meteo -> {om}")
        except Exception as exc:  # noqa: BLE001 - fallback source by design
            nasa = om.with_name(om.stem.replace("open_meteo", "nasa_power") + ".json")
            print(f"Open-Meteo failed ({exc}); falling back to NASA POWER -> {nasa}")
            weather.fetch_nasa_power(lat, lon, start, end, nasa)
    if pvgis_cache().exists():
        print(f"cached: {pvgis_cache()}")
    else:
        weather.fetch_pvgis_tmy(lat, lon, pvgis_cache())
        print(f"fetched PVGIS TMY -> {pvgis_cache()}")


def load_hourly(scn: dict) -> tuple[pd.DataFrame, Path, str]:
    om = open_meteo_cache(scn)
    if om.exists():
        return weather.load_open_meteo(om), om, "open_meteo_archive"
    nasa = om.with_name(om.stem.replace("open_meteo", "nasa_power") + ".json")
    if nasa.exists():
        return weather.load_nasa_power(nasa), nasa, "nasa_power_hourly"
    raise FileNotFoundError(f"no cached weather at {om}; run `make fetch-weather` once (needs internet)")


# ---------------------------------------------------------------- scenario
def scenario(_args=None, dataset_id: str = "thar1_demo_2024", period: tuple[str, str] | None = None) -> dict:
    from app.scenarios import generator  # the generator is not an engine; only this command imports it

    scn = load_scenario(dataset_id)
    plant = load_plant(PLANT_ID)
    start, end = period or (scn["period"]["start"], scn["period"]["end"])
    index = interval_index(start, end)
    hourly, wpath, wsource = load_hourly(scn)
    w15 = weather15.downscale(hourly, index, plant["location"]["lat"], plant["location"]["lon"])
    out = generator.generate(scn, plant, w15)
    with get_engine().begin() as conn:
        n = write_scenario(conn, dataset_id, scn, plant, out, wpath, wsource)
    gt = get_settings().configs_dir.parent / scn["ground_truth"]["path"]
    gt.parent.mkdir(parents=True, exist_ok=True)
    gt.write_text(json.dumps(out.ground_truth, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"scenario {dataset_id}: {n} measurement rows; ground truth -> {gt}")
    return out.ground_truth


def write_scenario(conn: Connection, dataset_id: str, scn: dict, plant: dict, out, wpath: Path, wsource: str) -> int:
    upsert_dataset(conn, dataset_id, PLANT_ID, "synthetic", scn, seed=scn["seed"])
    assets = sync_twin(conn, PLANT_ID)
    by_name = {a.name: a.id for a in assets}
    inv_ids = [by_name[n] for n in out.inverters]
    ws_id = by_name[plant["weather_station"]["id"]]
    meter_id = by_name[plant["meters"][0]["id"]]
    w_batch = register_batch(
        conn,
        dataset_id,
        wsource,
        sha256_file(wpath),
        "weather_estimated",
        notes="hourly reanalysis downscaled to 15 min (clear-sky index)",
    )
    s_batch = register_batch(
        conn,
        dataset_id,
        f"scenario:{dataset_id}.yaml",
        sha256_file(scenario_path(dataset_id)),
        "synthetic_scenario",
        notes=f"seed {scn['seed']}",
    )
    idx = out.index
    n_t = len(idx)
    frames = []

    def block(asset_ids, quantity, values, unit, kind, batch, text_values=None, mask=None):
        a = np.repeat(np.asarray(asset_ids, dtype=object)[None, :], n_t, axis=0)
        t = np.repeat(idx.to_numpy()[:, None], len(asset_ids), axis=1)
        m = np.ones_like(a, dtype=bool) if mask is None else mask
        df = pd.DataFrame(
            {
                "asset_id": a[m],
                "quantity": quantity,
                "ts_start": t[m],
                "value": None if values is None else np.asarray(values, dtype=float)[m],
                "value_text": None if text_values is None else np.asarray(text_values, dtype=object)[m],
                "unit": unit,
                "source_kind": kind,
                "batch_id": batch,
            }
        )
        frames.append(df)

    block(inv_ids, "ac_power_kw", out.ac_kw, "kW", "synthetic_scenario", s_batch, mask=out.reported)
    block(inv_ids, "status", None, "code", "synthetic_scenario", s_batch, text_values=out.status, mask=out.reported)
    block(inv_ids, "heartbeat", out.heartbeat, "count", "synthetic_scenario", s_batch)
    block([PLANT_ID], "status", None, "code", "synthetic_scenario", s_batch, text_values=out.plant_status[:, None])
    block([PLANT_ID], "setpoint_kw", out.setpoint_kw[:, None], "kW", "synthetic_scenario", s_batch)
    block([meter_id], "energy_export_kwh", out.meter_kwh[:, None], "kWh", "synthetic_scenario", s_batch)
    w = out.weather
    t_mod = w["t_cell"] - w["poa"] / 1000.0 * 3.0  # SAPM ΔT = 3 °C at 1,000 W/m²
    for q, col, unit in (
        ("ghi_wm2", "ghi", "W/m2"),
        ("dni_wm2", "dni", "W/m2"),
        ("dhi_wm2", "dhi", "W/m2"),
        ("t_amb_c", "temp_air", "degC"),
        ("wind_ms", "wind_speed", "m/s"),
        ("precip_mm", "precip_mm", "mm"),
    ):
        block([ws_id], q, w[col].to_numpy()[:, None], unit, "weather_estimated", w_batch)
    block([ws_id], "poa_wm2", w["poa"].to_numpy()[:, None], "W/m2", "modeled", w_batch)
    block([ws_id], "t_mod_c", t_mod.to_numpy()[:, None], "degC", "modeled", w_batch)

    meas = pd.concat(frames, ignore_index=True)
    meas["dataset_id"] = dataset_id
    meas["interval_s"] = 900
    meas["quality"] = flags.flag_measurements(meas, float(plant["inverter"]["ac_kw_each"]))
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
    n = write_measurements(conn, dataset_id, meas[cols], assets=[a.id for a in assets])

    log = pd.DataFrame(
        [
            {
                "id": stable_uuid("oplog", dataset_id, r["asset"], r["kind"], r["at"]),
                "dataset_id": dataset_id,
                "asset_id": by_name.get(r["asset"], r["asset"]),
                "kind": r["kind"],
                "at": r["at"],
                "note": r["note"],
                "source_kind": "synthetic_scenario",
            }
            for r in out.operator_log
        ]
    )
    replace_rows(conn, "operator_log", {"dataset_id": dataset_id}, log)
    return n


# ---------------------------------------------------------------- pipeline steps
def _measurements(conn: Connection, dataset_id: str, quantities: list[str]) -> pd.DataFrame:
    return pd.read_sql(
        text(
            "SELECT asset_id, quantity, ts_start, value, value_text, quality::text AS quality "
            "FROM measurement WHERE dataset_id = :d AND quantity = ANY(:q)"
        ),
        conn,
        params={"d": dataset_id, "q": quantities},
    )


def _index(conn: Connection, dataset_id: str) -> pd.DatetimeIndex:
    lo, hi = conn.execute(
        text("SELECT min(ts_start), max(ts_start) FROM measurement WHERE dataset_id = :d"), {"d": dataset_id}
    ).one()
    return pd.date_range(pd.Timestamp(lo).tz_convert("UTC"), pd.Timestamp(hi).tz_convert("UTC"), freq="15min")


def step_quality(conn: Connection, dataset_id: str) -> None:
    plant = load_plant(PLANT_ID)
    inv = [a.id for a in build_assets(plant) if a.kind == "inverter"]
    meas = _measurements(conn, dataset_id, ["ac_power_kw", "status", "heartbeat"])
    meas["ts_start"] = pd.to_datetime(meas["ts_start"], utc=True)
    actual = validated.energy_actual(meas, inv, _index(conn, dataset_id), dataset_id)
    replace_rows(conn, "actual_output", {"dataset_id": dataset_id}, actual)
    print(f"quality: actual_output {len(actual)} rows, no_data {int((actual['quality'] == 'no_data').sum())}")


def _weather(conn: Connection, dataset_id: str) -> pd.DataFrame:
    ws = _measurements(conn, dataset_id, ["ghi_wm2", "dni_wm2", "dhi_wm2", "t_amb_c", "wind_ms", "poa_wm2"])
    ws["ts_start"] = pd.to_datetime(ws["ts_start"], utc=True)
    w = ws.pivot(index="ts_start", columns="quantity", values="value").sort_index()
    return w.rename(
        columns={
            "ghi_wm2": "ghi",
            "dni_wm2": "dni",
            "dhi_wm2": "dhi",
            "t_amb_c": "temp_air",
            "wind_ms": "wind_speed",
            "poa_wm2": "poa_sensor",
        }
    )


def step_expected(conn: Connection, dataset_id: str) -> None:
    plant = load_plant(PLANT_ID)
    p = model.ChainParams.from_plant(plant)
    w = _weather(conn, dataset_id)
    chain = model.run_chain(w, p, INTERVAL_H)
    inv = [a.id for a in build_assets(plant) if a.kind == "inverter"]
    actual = pd.read_sql(
        text(
            "SELECT asset_id, ts_start, e_kwh, quality::text AS quality, status FROM actual_output "
            "WHERE dataset_id = :d"
        ),
        conn,
        params={"d": dataset_id},
    )
    actual["ts_start"] = pd.to_datetime(actual["ts_start"], utc=True)
    plant_status = _plant_status(conn, dataset_id)
    sigma, calib = band_sigma(actual, chain, plant_status, len(inv))
    batch = conn.execute(
        text("SELECT id FROM source_batch WHERE dataset_id = :d AND source_kind = 'weather_estimated'"),
        {"d": dataset_id},
    ).scalar_one()
    inputs_hash = sha256_hash(
        {
            "weather_batch": str(batch),
            "plant_config": sha256_file(plant_config_path(PLANT_ID)),
            "model_version": model.MODEL_VERSION,
            "chain": p.digest(),
        }
    )
    n_t = len(chain)
    rows = pd.DataFrame(
        {
            "dataset_id": dataset_id,
            "asset_id": np.repeat(inv, n_t),
            "ts_start": np.tile(chain.index.to_numpy(), len(inv)),
            "interval_s": 900,
            "poa_wm2": np.tile(chain["poa"].to_numpy(), len(inv)),
            "t_cell_c": np.tile(chain["t_cell"].to_numpy(), len(inv)),
            "e_potential_kwh": np.tile(chain["e_potential_kwh"].to_numpy(), len(inv)),
            "band_rel": 1.96 * sigma,
            "clipped": np.tile(chain["clipped"].to_numpy(), len(inv)),
            "model_version": model.MODEL_VERSION,
            "inputs_hash": inputs_hash,
        }
    )
    replace_rows(conn, "expected_output", {"dataset_id": dataset_id, "model_version": model.MODEL_VERSION}, rows)
    print(f"expected: {len(rows)} rows; sigma_rel {sigma:.4f} (band ±{1.96 * sigma:.4f}) from {calib}")


def _plant_status(conn: Connection, dataset_id: str) -> pd.Series:
    s = _measurements(conn, dataset_id, ["status"])
    s = s[s["asset_id"] == PLANT_ID]
    return pd.Series(s["value_text"].to_numpy(), index=pd.to_datetime(s["ts_start"], utc=True)).sort_index()


def band_sigma(actual: pd.DataFrame, chain: pd.DataFrame, plant_status: pd.Series, n_inv: int) -> tuple[float, list]:
    """σ_rel on healthy, clean, unclipped, unconstrained daylight intervals of the first 7 clean days (docs/02 §3.4)."""
    ws = pd.DataFrame({"ts_start": chain.index, "poa": chain["poa"].to_numpy(), "ok": True})
    days = realdata.clean_days(actual, ws, n_inv)[:7]
    f = actual.merge(chain[["poa", "e_potential_kwh", "clipped"]], left_on="ts_start", right_index=True)
    f["date"] = f["ts_start"].dt.tz_convert(PLANT_TZ).dt.date
    f["plant"] = f["ts_start"].map(plant_status)
    sel = f[
        f["date"].isin(days)
        & (f["quality"] == "ok")
        & (f["status"] == "RUNNING")
        & (f["plant"] == "RUNNING")
        & ~f["clipped"]
        & (f["poa"] >= realdata.FIT_MIN_IRR)
    ]
    ratio = sel["e_kwh"] / sel["e_potential_kwh"]
    return float(ratio.std(ddof=1)), [str(d) for d in days]


def step_detect(conn: Connection, dataset_id: str) -> None:
    plant = load_plant(PLANT_ID)
    codes = plant["status_codes"]
    meas = _measurements(conn, dataset_id, ["status", "setpoint_kw"])
    meas["ts_start"] = pd.to_datetime(meas["ts_start"], utc=True)
    st = meas[meas["quantity"] == "status"]
    series = {
        a: pd.Series(g["value_text"].to_numpy(), index=g["ts_start"]).sort_index() for a, g in st.groupby("asset_id")
    }
    plant_series = {PLANT_ID: series.pop(PLANT_ID)}
    sp = meas[meas["quantity"] == "setpoint_kw"]
    setpoint = pd.Series(sp["value"].to_numpy(), index=sp["ts_start"]).sort_index()
    events = status.detect(series, codes["inverter"], "inverter") + status.detect(
        plant_series, codes["plant"], "plant", setpoint
    )

    actual = pd.read_sql(
        text(
            "SELECT asset_id, ts_start, e_kwh, quality::text AS quality, status FROM actual_output "
            "WHERE dataset_id = :d"
        ),
        conn,
        params={"d": dataset_id},
    )
    actual["ts_start"] = pd.to_datetime(actual["ts_start"], utc=True)
    normal = {c for c, e in codes["inverter"].items() if e.get("normal")} - {"CURTAILED"}
    eligible = actual[actual["status"].isin(normal) & actual["ts_start"].map(plant_series[PLANT_ID]).eq("RUNNING")]
    w = _weather(conn, dataset_id)
    ratios = peer.daily_peer_ratio(eligible, w["poa_sensor"] > 0)
    for e in peer.detect(ratios):
        start = pd.Timestamp(e["first_day"]).tz_localize(PLANT_TZ).tz_convert("UTC")
        events.append(
            {
                "asset_id": e["asset_id"],
                "category": "underperformance",
                "cause_code": "PEER_DEVIATION",
                "start_ts": start,
                "end_ts": None,
                "controllable": True,
                "confidence": "suspected",
                "setpoint_kw": None,
                "evidence": {"rules": ["peer_deviation"], "metrics": {k: str(v) for k, v in e.items()}},
            }
        )
        last = (pd.Timestamp(e["last_day"]) + pd.Timedelta(days=1)).tz_localize(PLANT_TZ).tz_convert("UTC")
        if last < actual["ts_start"].max():
            events[-1]["end_ts"] = last
    write_events(conn, dataset_id, events)
    cats = pd.Series([e["category"] for e in events]).value_counts().to_dict()
    print(f"detect: {len(events)} events {cats}")


def write_events(conn: Connection, dataset_id: str, events: list[dict]) -> None:
    conn.execute(text("DELETE FROM event WHERE dataset_id = :d"), {"d": dataset_id})
    rows = [
        {
            "id": stable_uuid("event", dataset_id, e["asset_id"], e["cause_code"], e["start_ts"]),
            "dataset_id": dataset_id,
            **e,
            "source_kind": "derived",
        }
        for e in events
    ]
    if rows:
        df = pd.DataFrame(rows)[
            [
                "id",
                "dataset_id",
                "asset_id",
                "category",
                "cause_code",
                "start_ts",
                "end_ts",
                "controllable",
                "confidence",
                "evidence",
                "setpoint_kw",
                "source_kind",
            ]
        ]
        copy_frame(conn, "event", df)
