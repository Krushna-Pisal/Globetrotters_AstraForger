"""Tiny Kaggle-format CSVs for tests (test fixtures only — never loaded into a demo dataset).

Uses the real SOURCE_KEYs from configs/plant/kgl_p2.yaml so the adapter's key mapping is exercised.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from app.twin.loader import load_plant


def write_kaggle_fixture(directory: Path, days: int = 10, drop: int = 0, duplicate: bool = False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    plant = load_plant("KGL-P2")
    keys = [i["source_key"] for i in plant["hierarchy"]["inverters"]]
    local = pd.date_range("2020-05-15 00:00", periods=days * 96, freq="15min")
    hour = local.hour + local.minute / 60
    shape = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None)
    irr = 1.0 * shape  # kW/m², like the real file
    rows = []
    for n, key in enumerate(keys):
        ac = 1200 * shape * (1 + 0.01 * (n % 5 - 2))
        energy = pd.Series(ac * 0.25).groupby(local.date).cumsum().to_numpy()
        for t, a, e in zip(local, ac, energy, strict=True):
            rows.append((t.strftime("%Y-%m-%d %H:%M:%S"), 4136001, key, a / 0.978, a, e, 1_000_000 + e))
    gen = pd.DataFrame(
        rows, columns=["DATE_TIME", "PLANT_ID", "SOURCE_KEY", "DC_POWER", "AC_POWER", "DAILY_YIELD", "TOTAL_YIELD"]
    )
    if drop:
        gen = gen.drop(gen.index[100 : 100 + drop])
    if duplicate:
        gen = pd.concat([gen, gen.iloc[[500]]]).sort_index(kind="stable")
    gen.to_csv(directory / "Plant_2_Generation_Data.csv", index=False)
    ws = pd.DataFrame(
        {
            "DATE_TIME": local.strftime("%Y-%m-%d %H:%M:%S"),
            "PLANT_ID": 4136001,
            "SOURCE_KEY": plant["weather_station"]["source_key"],
            "AMBIENT_TEMPERATURE": 30.0,
            "MODULE_TEMPERATURE": 25 + 30 * shape,
            "IRRADIATION": irr,
        }
    )
    ws.to_csv(directory / "Plant_2_Weather_Sensor_Data.csv", index=False)
    p1 = gen.head(200).copy()
    p1["DATE_TIME"] = pd.to_datetime(p1["DATE_TIME"]).dt.strftime("%d-%m-%Y %H:%M")
    p1["DC_POWER"] = p1["AC_POWER"] * 10.2
    p1.to_csv(directory / "Plant_1_Generation_Data.csv", index=False)
    ws.head(200).to_csv(directory / "Plant_1_Weather_Sensor_Data.csv", index=False)
    return directory
