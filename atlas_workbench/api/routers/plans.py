"""POST /plans/subset and POST /plans/execution route handlers."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from atlas_workbench.api.schemas import (
    ExecutionPlanRequest,
    ExecutionPlanResponse,
    SubsetPlanRequest,
    SubsetPlanResponse,
)
from atlas_workbench.core.execution_planner import build_execution_plan
from atlas_workbench.core.stream_decision import decide_stream_vs_cache
from atlas_workbench.core.subset_planner import SubsetPlan, select_subset
from atlas_workbench.db.models import ExecutionPlan, FileManifest, ManifestSummary
from atlas_workbench.db.models import SubsetPlan as SubsetPlanRow
from atlas_workbench.db.session import get_session

router = APIRouter(tags=["plans"])


@router.post("/plans/subset", response_model=SubsetPlanResponse)
def build_subset(
    request: SubsetPlanRequest, session: Session = Depends(get_session)
) -> SubsetPlanResponse:
    """Build a deterministic subset plan from an existing manifest."""
    manifest_row = session.query(ManifestSummary).filter_by(id=int(request.manifest_id)).first()
    if manifest_row is None:
        raise HTTPException(status_code=404, detail="Manifest not found")

    file_rows = session.query(FileManifest).filter_by(manifest_summary_id=manifest_row.id).all()
    urls = [r.file_url_root for r in file_rows]

    # Determine collection_type from dataset_ref
    dataset_ref = manifest_row.dataset_ref
    if "410470" in dataset_ref or dataset_ref.startswith("dsid:"):
        collection_type = "mc"
    else:
        collection_type = "collision"

    plan: SubsetPlan = select_subset(
        urls=urls,
        collection_type=collection_type,
        n=request.n,
        dataset_ref=dataset_ref,
    )

    # Persist
    row = SubsetPlanRow(
        algorithm_version=plan.algorithm_version,
        n=plan.n,
        hashing_method=plan.hashing_method,
        selected_files=json.dumps(plan.selected_files),
        plan_hash=plan.plan_hash,
        manifest_summary_id=manifest_row.id,
    )
    session.add(row)
    session.commit()

    return SubsetPlanResponse(
        plan_id=str(row.id),
        algorithm_version=plan.algorithm_version,
        n=plan.n,
        hashing_method=plan.hashing_method,
        selected_files=plan.selected_files,
        plan_hash=plan.plan_hash,
        collection_type=collection_type,
    )


@router.post("/plans/execution", response_model=ExecutionPlanResponse)
def build_execution(
    request: ExecutionPlanRequest, session: Session = Depends(get_session)
) -> ExecutionPlanResponse:
    """Build a pinned execution plan from an existing subset plan."""
    subset_row = session.query(SubsetPlanRow).filter_by(id=int(request.subset_plan_id)).first()
    if subset_row is None:
        raise HTTPException(status_code=404, detail="Subset plan not found")

    selected_files: list[str] = json.loads(subset_row.selected_files)
    total_bytes = sum(len(u.encode()) for u in selected_files)  # proxy when size_bytes unknown

    stream_decision = decide_stream_vs_cache(total_bytes)
    plan = build_execution_plan(
        selected_files=selected_files,
        stream_decision=stream_decision,
    )

    row = ExecutionPlan(
        container_image_tag=plan.container_image_tag,
        command=plan.command,
        pinned_packages=json.dumps(plan.pinned_packages),
        env_vars=json.dumps(plan.env_vars),
        expected_inputs=json.dumps(plan.expected_inputs),
        expected_outputs=json.dumps(plan.expected_outputs),
        subset_plan_id=subset_row.id,
    )
    session.add(row)
    session.commit()

    return ExecutionPlanResponse(
        container_image_tag=plan.container_image_tag,
        command=plan.command,
        pinned_packages=plan.pinned_packages,
        env_vars=plan.env_vars,
        expected_inputs=plan.expected_inputs,
        expected_outputs=plan.expected_outputs,
        mc_weight_fields=plan.mc_weight_fields,
        cache_on=plan.cache_on,
        cache_location=plan.cache_location,
        max_cache_size_bytes=plan.max_cache_size_bytes,
    )
