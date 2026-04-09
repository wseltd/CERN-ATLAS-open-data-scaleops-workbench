"""SQLAlchemy 2.0 ORM models for the ATLAS workbench control-plane state store.

JSON fields are stored as Text; callers are responsible for json.dumps/json.loads.
BigInteger is mandatory for event_count and size_bytes: 9,058,437,931 events
exceeds a signed 32-bit integer.

No relationship() associations, no Alembic, no async — pure persistence concern.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Release(Base):
    """Top-level ATLAS open-data release record (e.g. record 80020)."""

    __tablename__ = "release"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # record_id and doi are control-plane keys — must never be None
    record_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    doi: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[Optional[str]]
    total_size_tib: Mapped[Optional[float]]
    file_count: Mapped[Optional[int]]
    # BigInteger: 9B+ events in the full release exceed int32
    event_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    release_tag: Mapped[Optional[str]]


class Collection(Base):
    """Child collection under a release (collision or simulated MC)."""

    __tablename__ = "collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    record_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    doi: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[Optional[str]]
    collection_type: Mapped[str] = mapped_column(nullable=False)
    size_tib: Mapped[Optional[float]]
    file_count: Mapped[Optional[int]]
    event_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    release_id: Mapped[Optional[int]] = mapped_column(ForeignKey("release.id"))


class Dataset(Base):
    """Per-DSID dataset metadata within a collection (e.g. DSID 410470 ttbar)."""

    __tablename__ = "dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    dsid: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[Optional[str]]
    process_type: Mapped[Optional[str]]
    # MC event weight = cross_section * filter_efficiency * k_factor — all three required together
    cross_section: Mapped[Optional[float]]
    filter_efficiency: Mapped[Optional[float]]
    k_factor: Mapped[Optional[float]]
    collection_id: Mapped[Optional[int]] = mapped_column(ForeignKey("collection.id"))


class ManifestSummary(Base):
    """Immutable summary artifact per manifest build run."""

    __tablename__ = "manifest_summary"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    dataset_ref: Mapped[str] = mapped_column(nullable=False)
    release_tag: Mapped[Optional[str]]
    file_count: Mapped[int] = mapped_column(nullable=False)
    protocol: Mapped[str] = mapped_column(nullable=False)
    # stable_hash: sha256 over ordered file list — used for deterministic subset selection
    stable_hash: Mapped[str] = mapped_column(nullable=False)


class FileManifest(Base):
    """Per-file inventory row; both root:// and https:// URLs recorded where available."""

    __tablename__ = "file_manifest"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # dataset_ref and file_url_root are control-plane keys — must never be None
    dataset_ref: Mapped[str] = mapped_column(nullable=False)
    file_url_root: Mapped[str] = mapped_column(nullable=False)
    file_url_https: Mapped[Optional[str]]
    # BigInteger: individual ROOT files can exceed 4 GiB
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    source_tool: Mapped[str] = mapped_column(nullable=False)
    discovered_at: Mapped[Optional[datetime]]
    manifest_summary_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("manifest_summary.id")
    )


class SubsetPlan(Base):
    """Deterministic subset selection artifact (v0.1 hash-sampling algorithm)."""

    __tablename__ = "subset_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    algorithm_version: Mapped[str] = mapped_column(nullable=False)
    n: Mapped[int] = mapped_column(nullable=False)
    hashing_method: Mapped[str] = mapped_column(nullable=False)
    # selected_files: JSON array stored as Text — callers do json.dumps/loads
    selected_files: Mapped[str] = mapped_column(Text, nullable=False)
    plan_hash: Mapped[str] = mapped_column(nullable=False)
    manifest_summary_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("manifest_summary.id")
    )


class ExecutionPlan(Base):
    """Pinned execution environment and command for a validation or analysis run."""

    __tablename__ = "execution_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # container_image_tag must include the explicit digest/tag — no 'latest'
    container_image_tag: Mapped[str] = mapped_column(nullable=False)
    command: Mapped[str] = mapped_column(nullable=False)
    # JSON arrays/objects stored as Text
    pinned_packages: Mapped[str] = mapped_column(Text, nullable=False)
    env_vars: Mapped[Optional[str]] = mapped_column(Text)
    expected_inputs: Mapped[Optional[str]] = mapped_column(Text)
    expected_outputs: Mapped[Optional[str]] = mapped_column(Text)
    subset_plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subset_plan.id"))


class ProvenanceRecord(Base):
    """Citation and license provenance for datasets used in a run."""

    __tablename__ = "provenance_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # JSON arrays stored as Text
    record_ids: Mapped[str] = mapped_column(Text, nullable=False)
    dois: Mapped[str] = mapped_column(Text, nullable=False)
    citation_text: Mapped[str] = mapped_column(nullable=False)
    license: Mapped[str] = mapped_column(nullable=False)
    run_id: Mapped[Optional[str]]


class ValidationReport(Base):
    """Outcome of a validation run against live ATLAS open data."""

    __tablename__ = "validation_report"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_logs: Mapped[Optional[str]]
    # BigInteger: bytes_read can exceed 4 GiB for large ROOT file reads
    bytes_read: Mapped[Optional[int]] = mapped_column(BigInteger)
    wall_time: Mapped[Optional[float]]
    summary_metrics: Mapped[Optional[str]] = mapped_column(Text)
    execution_plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("execution_plan.id")
    )


class EvalRun(Base):
    """Result of an evaluation run over the 20-question eval fixture set."""

    __tablename__ = "eval_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    run_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    questions_count: Mapped[int] = mapped_column(nullable=False)
    correct_count: Mapped[int] = mapped_column(nullable=False)
    # JSON array of per-question result objects stored as Text
    results: Mapped[str] = mapped_column(Text, nullable=False)
