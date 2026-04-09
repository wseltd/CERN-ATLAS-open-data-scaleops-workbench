"""POST /validate/run and GET /evidence/latest route handlers."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from atlas_workbench.api.schemas import (
    EvidenceResponse,
    ValidateRunRequest,
    ValidationReportResponse,
)
from atlas_workbench.core.subset_planner import SubsetPlan
from atlas_workbench.core.validator import run_validation
from atlas_workbench.db.models import ManifestSummary, ValidationReport
from atlas_workbench.db.models import SubsetPlan as SubsetPlanRow
from atlas_workbench.db.session import get_session

router = APIRouter(tags=["validate", "evidence"])


@router.post("/validate/run", response_model=ValidationReportResponse)
def validate_run(
    request: ValidateRunRequest, session: Session = Depends(get_session)
) -> ValidationReportResponse:
    """Run live validation against ATLAS Open Data xrootd endpoints."""
    subset_row = session.query(SubsetPlanRow).filter_by(id=int(request.subset_plan_id)).first()
    if subset_row is None:
        raise HTTPException(status_code=404, detail="Subset plan not found")

    selected_files: list[str] = json.loads(subset_row.selected_files)
    manifest_row = (
        (session.query(ManifestSummary).filter_by(id=subset_row.manifest_summary_id).first())
        if subset_row.manifest_summary_id
        else None
    )

    collection_type = "mc"
    if manifest_row and manifest_row.dataset_ref:
        ref = manifest_row.dataset_ref
        if "410470" not in ref and not ref.startswith("dsid:"):
            collection_type = "collision"

    plan = SubsetPlan(
        plan_id=str(subset_row.id),
        algorithm_version=subset_row.algorithm_version,
        hashing_method=subset_row.hashing_method,
        collection_type=collection_type,
        n=subset_row.n,
        selected_files=selected_files,
        plan_hash=subset_row.plan_hash,
    )

    report = run_validation(plan, protocol=request.protocol)

    report_row = ValidationReport(
        success=report.success,
        error_logs="\n".join(report.error_logs) if report.error_logs else None,
        bytes_read=report.bytes_read,
        wall_time=report.wall_time,
        summary_metrics=json.dumps(report.summary_metrics),
    )
    session.add(report_row)
    session.commit()

    return ValidationReportResponse(
        success=report.success,
        error_logs=report.error_logs,
        bytes_read=report.bytes_read,
        wall_time=report.wall_time,
        numentries_mc=report.numentries_mc,
        numentries_collision=report.numentries_collision,
        branches_read=report.branches_read,
        summary_metrics=report.summary_metrics,
    )


@router.get("/evidence/latest", response_model=EvidenceResponse)
def evidence_latest(session: Session = Depends(get_session)) -> EvidenceResponse:
    """Return a summary of the latest evidence: validation reports and artifact counts."""
    reports = session.query(ValidationReport).order_by(ValidationReport.id.desc()).limit(5).all()
    manifest_count = session.query(ManifestSummary).count()
    subset_plan_count = session.query(SubsetPlanRow).count()

    report_responses = [
        ValidationReportResponse(
            success=r.success,
            error_logs=r.error_logs.split("\n") if r.error_logs else [],
            bytes_read=r.bytes_read or 0,
            wall_time=r.wall_time or 0.0,
            numentries_mc=None,
            numentries_collision=None,
            branches_read=[],
            summary_metrics=json.loads(r.summary_metrics) if r.summary_metrics else {},
        )
        for r in reports
    ]

    return EvidenceResponse(
        run_id=str(reports[0].id) if reports else None,
        validation_reports=report_responses,
        manifest_count=manifest_count,
        subset_plan_count=subset_plan_count,
    )
