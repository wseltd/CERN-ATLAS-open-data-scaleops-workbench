"""POST /manifests/build and GET /manifests/{manifest_id} route handlers."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from atlas_workbench.api.schemas import ManifestBuildRequest, ManifestSummaryResponse
from atlas_workbench.core.manifest_builder import build_manifest
from atlas_workbench.db.models import FileManifest, ManifestSummary
from atlas_workbench.db.session import get_session

router = APIRouter(tags=["manifests"])


@router.post("/manifests/build", response_model=ManifestSummaryResponse)
def build(
    request: ManifestBuildRequest, session: Session = Depends(get_session)
) -> ManifestSummaryResponse:
    """Build and persist a file manifest for a dataset reference."""
    result = build_manifest(
        dataset_ref=request.collection_id,
        protocol=request.protocol,
    )
    summary_row = ManifestSummary(
        dataset_ref=result.dataset_ref,
        release_tag=result.release_tag,
        file_count=result.file_count,
        protocol=result.protocol,
        stable_hash=result.stable_hash,
    )
    session.add(summary_row)
    session.flush()

    now = datetime.now(tz=timezone.utc)
    for entry in result.files:
        row = FileManifest(
            dataset_ref=entry.dataset_ref,
            file_url_root=entry.file_url_root,
            file_url_https=entry.file_url_https,
            size_bytes=entry.size_bytes,
            source_tool=entry.source_tool,
            discovered_at=now,
            manifest_summary_id=summary_row.id,
        )
        session.add(row)

    session.commit()

    return ManifestSummaryResponse(
        manifest_id=str(summary_row.id),
        dataset_ref=result.dataset_ref,
        release_tag=result.release_tag,
        file_count=result.file_count,
        protocol=result.protocol,
        stable_hash=result.stable_hash,
    )


@router.get("/manifests/{manifest_id}", response_model=ManifestSummaryResponse)
def get_manifest(
    manifest_id: str, session: Session = Depends(get_session)
) -> ManifestSummaryResponse:
    row = session.query(ManifestSummary).filter_by(id=int(manifest_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return ManifestSummaryResponse(
        manifest_id=str(row.id),
        dataset_ref=row.dataset_ref,
        release_tag=row.release_tag or "",
        file_count=row.file_count,
        protocol=row.protocol,
        stable_hash=row.stable_hash,
    )
