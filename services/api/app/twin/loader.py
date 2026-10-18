"""Plant twin from configs/plant/*.yaml -> asset_template + asset rows (docs/04 §2)."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from sqlalchemy import Connection, text

from app.core.config import get_settings

TEMPLATES = {
    "solar_pv_fixed_tilt@1": ("plant", {"quantities": ["status", "setpoint_kw"]}),
    "block@1": ("block", {}),
    "pv_inverter@1": ("inverter", {"quantities": ["ac_power_kw", "dc_power_kw", "status", "heartbeat"]}),
    "meter@1": ("meter", {"quantities": ["energy_export_kwh"]}),
    "weather_station@1": ("weather_station", {"quantities": ["poa_wm2", "ghi_wm2", "t_mod_c", "t_amb_c", "wind_ms"]}),
    "bess_container@0-stub": ("bess", {"stub": True, "note": "schema-only proof of twin genericity (S5)"}),
}


@dataclass
class Asset:
    id: str
    plant_id: str
    parent_id: str | None
    kind: str
    template_id: str
    name: str
    attrs: dict = field(default_factory=dict)


def plant_config_path(plant_id: str) -> Path:
    name = {"THAR1": "thar1.yaml", "KGL-P2": "kgl_p2.yaml"}[plant_id]
    return get_settings().configs_dir / "plant" / name


def load_plant(plant_id: str) -> dict:
    return yaml.safe_load(plant_config_path(plant_id).read_text(encoding="utf-8"))["plant"]


def inverter_ids(plant: dict) -> list[str]:
    """Full asset ids of every inverter, in hierarchy order."""
    return [a.id for a in build_assets(plant) if a.kind == "inverter"]


def build_assets(plant: dict) -> list[Asset]:
    pid = plant["id"]
    assets = [Asset(pid, pid, None, "plant", plant["template"], plant["name"], {"capacity": plant.get("capacity")})]
    hierarchy = plant["hierarchy"]
    inv = plant.get("inverter", {})
    inv_attrs = {k: inv[k] for k in ("ac_kw_each", "dc_kwp_each", "rated_ac_kw_inferred") if k in inv}
    if "blocks" in hierarchy:
        for block in hierarchy["blocks"]:
            bid = f"{pid}/{block['id']}"
            assets.append(Asset(bid, pid, pid, "block", "block@1", block["id"]))
            for name in block["inverters"]:
                assets.append(Asset(f"{bid}/{name}", pid, bid, "inverter", "pv_inverter@1", name, dict(inv_attrs)))
    else:
        for item in hierarchy["inverters"]:
            attrs = dict(inv_attrs) | {"source_key": item["source_key"]}
            assets.append(Asset(f"{pid}/{item['id']}", pid, pid, "inverter", "pv_inverter@1", item["id"], attrs))
    for meter in plant.get("meters", []):
        assets.append(Asset(f"{pid}/{meter['id']}", pid, pid, "meter", "meter@1", meter["id"], {"role": meter["role"]}))
    ws = plant.get("weather_station")
    if ws:
        attrs = {"source_key": ws["source_key"]} if "source_key" in ws else {}
        assets.append(Asset(f"{pid}/{ws['id']}", pid, pid, "weather_station", "weather_station@1", ws["id"], attrs))
    return assets


def asset_by_name(plant: dict, name: str) -> str:
    """'INV-07' -> 'THAR1/B2/INV-07'; 'THAR1' -> 'THAR1'."""
    for a in build_assets(plant):
        if a.name == name or a.id == name:
            return a.id
    raise KeyError(name)


def sync_twin(conn: Connection, plant_id: str) -> list[Asset]:
    plant = load_plant(plant_id)
    for tid, (kind, schema) in TEMPLATES.items():
        conn.execute(
            text(
                "INSERT INTO asset_template (id, kind, schema) VALUES (:i, :k, CAST(:s AS jsonb)) "
                "ON CONFLICT (id) DO UPDATE SET schema = EXCLUDED.schema"
            ),
            {"i": tid, "k": kind, "s": json.dumps(schema)},
        )
    assets = build_assets(plant)
    for a in assets:
        conn.execute(
            text(
                "INSERT INTO asset (id, plant_id, parent_id, kind, template_id, name, attrs) "
                "VALUES (:id, :p, :par, :k, :t, :n, CAST(:a AS jsonb)) "
                "ON CONFLICT (id) DO UPDATE SET attrs = EXCLUDED.attrs, name = EXCLUDED.name"
            ),
            {
                "id": a.id,
                "p": a.plant_id,
                "par": a.parent_id,
                "k": a.kind,
                "t": a.template_id,
                "n": a.name,
                "a": json.dumps(a.attrs, default=str),
            },
        )
    return assets
