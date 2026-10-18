"""ORM models. Names and types are binding: they mirror docs/04_DATA_MODEL.md.

M0 covers the enums (docs/04 §1) and identity/twin/provenance tables (docs/04 §2). Later milestones add
their tables here together with a migration.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SOURCE_KINDS = (
    "measured",
    "weather_estimated",
    "modeled",
    "synthetic_scenario",
    "synthetic_reference",
    "synthetic_contract",
    "derived",
    "operator",
)
QUALITY_FLAGS = ("ok", "estimated", "no_data", "suspect")
EVENT_CATEGORIES = (
    "equipment_outage",
    "grid_unavailability",
    "curtailment",
    "comms_loss",
    "underperformance",
    "cleaning",
    "other",
)
CONFIDENCES = ("confirmed", "suspected")
CONTRACT_KINDS = ("ppa", "om", "loan")
WO_STATUSES = ("open", "acknowledged", "onsite", "restored", "verified")

# Types are created by the migration; models only reference them.
source_kind_enum = ENUM(*SOURCE_KINDS, name="source_kind", create_type=False)
quality_flag_enum = ENUM(*QUALITY_FLAGS, name="quality_flag", create_type=False)
event_category_enum = ENUM(*EVENT_CATEGORIES, name="event_category", create_type=False)
confidence_enum = ENUM(*CONFIDENCES, name="confidence", create_type=False)
contract_kind_enum = ENUM(*CONTRACT_KINDS, name="contract_kind", create_type=False)
wo_status_enum = ENUM(*WO_STATUSES, name="wo_status", create_type=False)


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "dataset"
    __table_args__ = (CheckConstraint("kind IN ('measured','synthetic')", name="dataset_kind_check"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plant_id: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    seed: Mapped[int | None] = mapped_column(BigInteger)
    config: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceBatch(Base):
    __tablename__ = "source_batch"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[str] = mapped_column(Text, ForeignKey("dataset.id"))
    source_name: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_kind: Mapped[str] = mapped_column(source_kind_enum)
    notes: Mapped[str | None] = mapped_column(Text)


class AssetTemplate(Base):
    __tablename__ = "asset_template"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    schema: Mapped[dict] = mapped_column(JSONB)


class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    plant_id: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[str | None] = mapped_column(Text, ForeignKey("asset.id"))
    kind: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(Text, ForeignKey("asset_template.id"))
    name: Mapped[str] = mapped_column(Text)
    attrs: Mapped[dict] = mapped_column(JSONB, server_default="{}")
