"""POST /seed and POST /query route handlers."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from atlas_workbench.api.schemas import (
    QueryRequest,
    QueryResponse,
    SeedRequest,
    SeedResponse,
)
from atlas_workbench.core import docs_seeder, metadata_seeder, query_engine
from atlas_workbench.db.session import get_session

router = APIRouter(tags=["seed", "query"])


@router.post("/seed", response_model=SeedResponse)
def seed(request: SeedRequest, session: Session = Depends(get_session)) -> SeedResponse:
    """Load structured metadata and docs corpus into the database."""
    meta_counts = metadata_seeder.seed(session, force=request.force)
    docs_count = docs_seeder.seed(session, force=request.force)
    total_collections = meta_counts.get("collections", 0)
    return SeedResponse(
        status="ok",
        collections_seeded=total_collections,
        docs_seeded=docs_count,
    )


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, session: Session = Depends(get_session)) -> QueryResponse:
    """Answer a question about the ATLAS release with evidence-backed structured output."""
    result = query_engine.answer(request.question, session)
    return QueryResponse(
        answer=result.answer,
        intent=result.intent,
        release_summary=result.release_summary,
        selected_collections=result.selected_collections,
        manifest_summary=result.manifest_summary,
        access_strategy=result.access_strategy,
        subset_plan=result.subset_plan,
        execution_plan=result.execution_plan,
        provenance_and_citation=result.provenance_and_citation,
        evidence=result.evidence,
        caveats=result.caveats,
    )
