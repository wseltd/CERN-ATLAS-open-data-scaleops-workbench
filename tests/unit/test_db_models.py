"""Unit tests for atlas_workbench.db.models.

These tests use SQLAlchemy's mapper inspection to verify column constraints
without requiring a live database. Inspection is stable across SQLAlchemy 2.x
and tests the schema definition, not runtime DB behaviour.

Test distribution is uneven by design: 7 tests target NOT NULL and FK
constraints (the risky control-plane invariants), 3 cover basic field
presence. This mirrors where the failure cost is highest.
"""

from sqlalchemy import Boolean
from sqlalchemy import inspect as sa_inspect

from atlas_workbench.db.models import (
    Collection,
    Dataset,
    EvalRun,
    ExecutionPlan,
    FileManifest,
    ManifestSummary,
    ProvenanceRecord,
    Release,
    SubsetPlan,
    ValidationReport,
)

ALL_MODELS = [
    Release,
    Collection,
    Dataset,
    FileManifest,
    ManifestSummary,
    SubsetPlan,
    ExecutionPlan,
    ProvenanceRecord,
    ValidationReport,
    EvalRun,
]


def _col(model, name):
    return sa_inspect(model).columns[name]


# ---------------------------------------------------------------------------
# NOT NULL constraint tests (risk surface — 7 tests)
# ---------------------------------------------------------------------------


def test_release_model_requires_record_id():
    """record_id is a control-plane key: missing it breaks manifest lookups."""
    col = _col(Release, "record_id")
    assert not col.nullable, "Release.record_id must be NOT NULL"
    assert col.unique, "Release.record_id must have a UNIQUE constraint"


def test_release_model_requires_doi():
    """doi drives citation provenance — a NULL doi silently omits attribution."""
    col = _col(Release, "doi")
    assert not col.nullable, "Release.doi must be NOT NULL"


def test_collection_model_has_release_fk():
    """release_id must carry a ForeignKey to release.id, not a bare int column.

    A bare integer without FK allows orphaned collections that break the
    collection-to-release hierarchy assumed by /collections/{id} lookups.
    """
    col = _col(Collection, "release_id")
    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "release.id" in fk_targets, (
        f"Collection.release_id must FK to release.id; got {fk_targets}"
    )


def test_file_manifest_requires_dataset_ref():
    """dataset_ref is the join key between FileManifest and Dataset lookups."""
    col = _col(FileManifest, "dataset_ref")
    assert not col.nullable, "FileManifest.dataset_ref must be NOT NULL"


def test_file_manifest_requires_file_url_root():
    """file_url_root is the xrootd streaming URL — a NULL here means no access path."""
    col = _col(FileManifest, "file_url_root")
    assert not col.nullable, "FileManifest.file_url_root must be NOT NULL"


def test_subset_plan_stores_algorithm_version():
    """algorithm_version column exists and is NOT NULL — required by acceptance criteria."""
    col = _col(SubsetPlan, "algorithm_version")
    assert not col.nullable, "SubsetPlan.algorithm_version must be NOT NULL"


def test_execution_plan_stores_container_image_tag():
    """container_image_tag column exists and is NOT NULL — required by acceptance criteria."""
    col = _col(ExecutionPlan, "container_image_tag")
    assert not col.nullable, "ExecutionPlan.container_image_tag must be NOT NULL"


def test_subset_plan_reproducibility_fields_not_null():
    """algorithm_version pins reproducibility; a NULL breaks the audit trail."""
    col = _col(SubsetPlan, "algorithm_version")
    assert not col.nullable, "SubsetPlan.algorithm_version must be NOT NULL"
    # selected_files must also be NOT NULL — a NULL here means no subset was recorded
    selected = _col(SubsetPlan, "selected_files")
    assert not selected.nullable, "SubsetPlan.selected_files must be NOT NULL"


def test_execution_plan_pinning_fields_not_null():
    """container_image_tag must be NOT NULL and carry the pinned image reference."""
    col = _col(ExecutionPlan, "container_image_tag")
    assert not col.nullable, "ExecutionPlan.container_image_tag must be NOT NULL"
    # pinned_packages must also be NOT NULL — unpinned packages break reproducibility
    pkgs = _col(ExecutionPlan, "pinned_packages")
    assert not pkgs.nullable, "ExecutionPlan.pinned_packages must be NOT NULL"


# ---------------------------------------------------------------------------
# Basic field presence and type tests (3 tests)
# ---------------------------------------------------------------------------


def test_validation_report_success_is_boolean():
    """success must be a Boolean column, not an integer disguised as bool.

    SQLAlchemy maps Python bool to BOOLEAN in most dialects, but without the
    explicit Boolean type the column may degrade to INTEGER on SQLite,
    silently accepting values like 2 that break tri-state confusion downstream.
    """
    col = _col(ValidationReport, "success")
    assert not col.nullable, "ValidationReport.success must be NOT NULL"
    assert isinstance(col.type, Boolean), (
        f"ValidationReport.success must be Boolean type; got {type(col.type)}"
    )


def test_eval_run_requires_run_id():
    """run_id is the external key for eval result retrieval — must be NOT NULL UNIQUE."""
    col = _col(EvalRun, "run_id")
    assert not col.nullable, "EvalRun.run_id must be NOT NULL"
    assert col.unique, "EvalRun.run_id must have a UNIQUE constraint"


def test_all_models_have_created_at():
    """Every model must have a created_at column with a server-side default.

    server_default=func.now() ensures the DB stamps rows on bulk inserts
    that bypass ORM-level defaults. Testing server_default presence catches
    the mistake of using Python-side default= instead.
    """
    for model in ALL_MODELS:
        col = _col(model, "created_at")
        assert col.server_default is not None, (
            f"{model.__name__}.created_at must have server_default=func.now()"
        )
        assert str(col.server_default.arg) != "", (
            f"{model.__name__}.created_at server_default must be a non-empty SQL expression"
        )
