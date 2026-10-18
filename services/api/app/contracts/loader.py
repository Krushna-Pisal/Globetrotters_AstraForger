"""Contract loaders (docs/03 §2). Separate functions so each engine can ask only for its own contract:
settlement -> load_ppa, om -> load_om, finance -> load_loan. INR values are parsed as Decimal from strings.
"""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml
from sqlalchemy import Connection, text

from app.core.config import get_settings


def _path(name: str) -> Path:
    return get_settings().configs_dir / "contracts" / name


def _read(name: str) -> tuple[dict, str]:
    raw = _path(name).read_bytes()
    return yaml.safe_load(raw)["contract"], hashlib.sha256(raw).hexdigest()


def D(value) -> Decimal:  # noqa: N802 - short, used for contract terms
    return Decimal(str(value))


@dataclass(frozen=True)
class PPA:
    id: str
    plant_id: str
    effective_from: str
    tariff: Decimal
    contracted_kw: Decimal
    declared_cuf: Decimal
    min_fraction: Decimal
    max_fraction: Decimal
    excess_rate_fraction: Decimal
    shortfall_rate_fraction: Decimal
    backdown_fraction: Decimal
    grid_threshold_h: Decimal
    grid_window_local: tuple[str, str]
    grid_rate_fraction: Decimal
    interpretation: str
    terms: dict
    sha256: str


@dataclass(frozen=True)
class OM:
    id: str
    plant_id: str
    effective_from: str
    annual_fee: Decimal
    guarantee: Decimal
    excluded_causes: tuple[str, ...]
    ld_rate: Decimal
    ld_cap_fraction: Decimal
    sla: dict
    cleaning_interval_days: int
    terms: dict
    sha256: str

    @property
    def ld_cap(self) -> Decimal:
        return self.annual_fee * self.ld_cap_fraction


@dataclass(frozen=True)
class Loan:
    id: str
    plant_id: str
    debt_service_annual: Decimal
    schedule: str
    sizing: Decimal
    lockup: Decimal
    default: Decimal
    terms: dict
    sha256: str


def load_ppa() -> PPA:
    c, sha = _read("ppa_v1.yaml")
    cl = c["clauses"]
    return PPA(
        id=c["id"],
        plant_id=c["plant_id"],
        effective_from=str(c["effective_from"]),
        tariff=D(c["tariff"]["base_inr_per_kwh"]),
        contracted_kw=D(c["contracted_capacity_kw"]),
        declared_cuf=D(c["cuf"]["declared_annual"]),
        min_fraction=D(c["cuf"]["min_fraction_of_declared"]),
        max_fraction=D(c["cuf"]["max_fraction_of_declared"]),
        excess_rate_fraction=D(cl["C4.2_excess_generation"]["rate_fraction_of_tariff"]),
        shortfall_rate_fraction=D(cl["C4.3_shortfall_compensation"]["rate_fraction_of_tariff"]),
        backdown_fraction=D(cl["C4.4_backdown_compensation"]["fraction"]),
        grid_threshold_h=D(cl["C4.5_grid_unavailability_compensation"]["threshold_hours_per_year"]),
        grid_window_local=tuple(cl["C4.5_grid_unavailability_compensation"]["count_window_local"]),
        grid_rate_fraction=D(cl["C4.5_grid_unavailability_compensation"]["rate_fraction_of_tariff"]),
        interpretation=c["interpretation"],
        terms=c,
        sha256=sha,
    )


def load_om() -> OM:
    c, sha = _read("om_v1.yaml")
    ag = c["availability_guarantee"]
    return OM(
        id=c["id"],
        plant_id=c["plant_id"],
        effective_from=str(c["effective_from"]),
        annual_fee=D(c["annual_fee_inr"]),
        guarantee=D(ag["guarantee"]),
        excluded_causes=tuple(ag["excluded_causes"]),
        ld_rate=D(ag["liquidated_damages"]["rate_inr_per_kwh"]),
        ld_cap_fraction=D(ag["liquidated_damages"]["cap_fraction_of_annual_fee"]),
        sla=c["response_sla"],
        cleaning_interval_days=int(c["cleaning"]["interval_days"]),
        terms=c,
        sha256=sha,
    )


def load_loan() -> Loan:
    c, sha = _read("loan_v1.yaml")
    cov = c["covenants"]
    return Loan(
        id=c["id"],
        plant_id=c["plant_id"],
        debt_service_annual=D(c["debt_service"]["annual_inr"]),
        schedule=c["debt_service"]["schedule"],
        sizing=D(cov["sizing_dscr"]),
        lockup=D(cov["lockup_dscr"]),
        default=D(cov["default_dscr"]),
        terms=c,
        sha256=sha,
    )


def register(conn: Connection, contract: PPA | OM | Loan, kind: str) -> None:
    """Upsert the parsed terms into `contract` (one row per contract id)."""
    conn.execute(
        text(
            "INSERT INTO contract (id, kind, plant_id, version, effective_from, terms, sha256, source_kind) "
            "VALUES (:i, :k, :p, 1, :e, CAST(:t AS jsonb), :s, 'synthetic_contract') "
            "ON CONFLICT (id) DO UPDATE SET terms = EXCLUDED.terms, sha256 = EXCLUDED.sha256"
        ),
        {
            "i": contract.id,
            "k": kind,
            "p": contract.plant_id,
            "e": contract.terms.get("effective_from", "2023-04-01"),
            "t": json.dumps(contract.terms, default=str),
            "s": contract.sha256,
        },
    )
