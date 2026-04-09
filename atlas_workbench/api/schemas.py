"""Pydantic v2 request/response schemas for all API endpoints.

extra='forbid' on all models: unexpected fields raise ValidationError at
construction time, making the contract machine-checkable without a live server.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.model_dump()!r})"


# ---- Seed -----------------------------------------------------------------------


class SeedRequest(_Strict):
    force: bool = False

    def __repr__(self) -> str:
        return f"SeedRequest(force={self.force!r})"


class SeedResponse(_Strict):
    status: str
    collections_seeded: int
    docs_seeded: int

    def __repr__(self) -> str:
        return f"SeedResponse(status={self.status!r}, collections={self.collections_seeded!r})"


# ---- Query ----------------------------------------------------------------------


class QueryRequest(_Strict):
    question: str

    def __repr__(self) -> str:
        return f"QueryRequest(question={self.question!r})"


class QueryResponse(_Strict):
    answer: str
    intent: str
    release_summary: dict[str, Any]
    selected_collections: list[dict[str, Any]]
    manifest_summary: dict[str, Any]
    access_strategy: dict[str, Any]
    subset_plan: dict[str, Any]
    execution_plan: dict[str, Any]
    provenance_and_citation: dict[str, Any]
    evidence: list[str]
    caveats: list[str]

    def __repr__(self) -> str:
        return f"QueryResponse(intent={self.intent!r}, answer={self.answer[:60]!r})"


# ---- Collections ----------------------------------------------------------------


class CollectionResponse(_Strict):
    record_id: str
    doi: str
    title: str | None
    collection_type: str
    size_tib: float | None
    file_count: int | None
    event_count: int | None

    def __repr__(self) -> str:
        return f"CollectionResponse(record_id={self.record_id!r}, type={self.collection_type!r})"


# ---- Manifests ------------------------------------------------------------------


class ManifestBuildRequest(_Strict):
    collection_id: str  # e.g. 'record:80001' or 'dsid:410470'
    protocol: Literal["root", "https"] = "root"

    def __repr__(self) -> str:
        return (
            f"ManifestBuildRequest(collection_id={self.collection_id!r},"
            f" protocol={self.protocol!r})"
        )


class ManifestSummaryResponse(_Strict):
    manifest_id: str
    dataset_ref: str
    release_tag: str
    file_count: int
    protocol: str
    stable_hash: str

    def __repr__(self) -> str:
        return (
            f"ManifestSummaryResponse(manifest_id={self.manifest_id!r},"
            f" file_count={self.file_count!r})"
        )


# ---- Plans: subset --------------------------------------------------------------


class SubsetPlanRequest(_Strict):
    manifest_id: str
    n: int | None = None

    def __repr__(self) -> str:
        return f"SubsetPlanRequest(manifest_id={self.manifest_id!r}, n={self.n!r})"


class SubsetPlanResponse(_Strict):
    plan_id: str
    algorithm_version: str
    n: int
    hashing_method: str
    selected_files: list[str]
    plan_hash: str
    collection_type: str

    def __repr__(self) -> str:
        return f"SubsetPlanResponse(plan_id={self.plan_id!r}, n={self.n!r})"


# ---- Plans: execution -----------------------------------------------------------


class ExecutionPlanRequest(_Strict):
    subset_plan_id: str

    def __repr__(self) -> str:
        return f"ExecutionPlanRequest(subset_plan_id={self.subset_plan_id!r})"


class ExecutionPlanResponse(_Strict):
    container_image_tag: str
    command: str
    pinned_packages: dict[str, str]
    env_vars: dict[str, str]
    expected_inputs: list[str]
    expected_outputs: list[str]
    mc_weight_fields: list[str]
    cache_on: bool
    cache_location: str | None
    max_cache_size_bytes: int

    def __repr__(self) -> str:
        return f"ExecutionPlanResponse(container_image_tag={self.container_image_tag!r})"


# ---- Validate -------------------------------------------------------------------


class ValidateRunRequest(_Strict):
    subset_plan_id: str
    protocol: Literal["root", "https"] = "root"

    def __repr__(self) -> str:
        return (
            f"ValidateRunRequest(subset_plan_id={self.subset_plan_id!r},"
            f" protocol={self.protocol!r})"
        )


class ValidationReportResponse(_Strict):
    success: bool
    error_logs: list[str]
    bytes_read: int
    wall_time: float
    numentries_mc: int | None
    numentries_collision: int | None
    branches_read: list[str]
    summary_metrics: dict[str, Any]

    def __repr__(self) -> str:
        return f"ValidationReportResponse(success={self.success!r}, bytes_read={self.bytes_read!r})"


# ---- Evidence -------------------------------------------------------------------


class EvidenceResponse(_Strict):
    run_id: str | None
    validation_reports: list[ValidationReportResponse]
    manifest_count: int
    subset_plan_count: int

    def __repr__(self) -> str:
        return f"EvidenceResponse(manifest_count={self.manifest_count!r})"


# ---- Eval -----------------------------------------------------------------------


class EvalRunRequest(_Strict):
    # no request body needed — runs all 20 questions
    def __repr__(self) -> str:
        return "EvalRunRequest()"


class EvalQuestionResult(_Strict):
    id: int
    question: str
    answer: str
    intent: str

    def __repr__(self) -> str:
        return f"EvalQuestionResult(id={self.id!r}, intent={self.intent!r})"


class EvalRunResponse(_Strict):
    run_id: str
    questions_count: int
    results: list[EvalQuestionResult]

    def __repr__(self) -> str:
        return f"EvalRunResponse(run_id={self.run_id!r}, questions_count={self.questions_count!r})"


class EvalResultsResponse(_Strict):
    run_id: str
    questions_count: int
    results: list[EvalQuestionResult]

    def __repr__(self) -> str:
        return f"EvalResultsResponse(run_id={self.run_id!r}, count={self.questions_count!r})"
