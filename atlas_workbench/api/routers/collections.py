"""GET /collections and GET /collections/{id} route handlers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from atlas_workbench.api.schemas import CollectionResponse
from atlas_workbench.db.models import Collection
from atlas_workbench.db.session import get_session

router = APIRouter(tags=["collections"])


def _to_response(row: Collection) -> CollectionResponse:
    return CollectionResponse(
        record_id=row.record_id,
        doi=row.doi,
        title=row.title,
        collection_type=row.collection_type,
        size_tib=row.size_tib,
        file_count=row.file_count,
        event_count=row.event_count,
    )


@router.get("/collections", response_model=list[CollectionResponse])
def list_collections(session: Session = Depends(get_session)) -> list[CollectionResponse]:
    rows = session.query(Collection).all()
    return [_to_response(r) for r in rows]


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: str, session: Session = Depends(get_session)
) -> CollectionResponse:
    row = session.query(Collection).filter_by(record_id=collection_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _to_response(row)
