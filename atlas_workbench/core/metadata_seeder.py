"""Metadata seeder: reads seed/release_metadata.json and upserts Release + Collection rows."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from atlas_workbench.db.models import Collection, Dataset, Release

_SEED_FILE = Path(__file__).parent.parent / "seed" / "release_metadata.json"


def _load_seed() -> dict:
    with _SEED_FILE.open() as fh:
        return json.load(fh)


def seed(session: Session, force: bool = False) -> dict[str, int]:
    """Upsert release and collection rows from the frozen seed fixture.

    Returns a dict with counts: {'releases': N, 'collections': N, 'datasets': N}.
    Idempotent: existing rows are updated in place when force=True, skipped otherwise.
    """
    data = _load_seed()
    counts: dict[str, int] = {"releases": 0, "collections": 0, "datasets": 0}

    # ---- Release ----
    rel_data = data["release"]
    existing_release = (
        session.query(Release).filter_by(record_id=str(rel_data["record_id"])).first()
    )
    if existing_release is None or force:
        if existing_release is None:
            release_new = Release(
                record_id=str(rel_data["record_id"]),
                doi=rel_data["doi"],
                title=rel_data.get("title"),
                total_size_tib=rel_data.get("total_size_tib"),
                file_count=rel_data.get("file_count"),
                event_count=rel_data.get("event_count"),
                release_tag=rel_data.get("release_tag"),
            )
            session.add(release_new)
        else:
            existing_release.doi = rel_data["doi"]
            existing_release.title = rel_data.get("title")
            existing_release.total_size_tib = rel_data.get("total_size_tib")
            existing_release.file_count = rel_data.get("file_count")
            existing_release.event_count = rel_data.get("event_count")
            existing_release.release_tag = rel_data.get("release_tag")
        counts["releases"] += 1

    session.flush()

    # Need the release PK for FKs
    release_row = session.query(Release).filter_by(record_id=str(rel_data["record_id"])).first()

    # ---- Collections ----
    for col_data in data.get("collections", []):
        existing_col = (
            session.query(Collection).filter_by(record_id=str(col_data["record_id"])).first()
        )
        if existing_col is None or force:
            if existing_col is None:
                collection_new = Collection(
                    record_id=str(col_data["record_id"]),
                    doi=col_data["doi"],
                    title=col_data.get("title"),
                    collection_type=col_data["collection_type"],
                    size_tib=col_data.get("size_tib"),
                    file_count=col_data.get("file_count"),
                    event_count=col_data.get("event_count"),
                    release_id=release_row.id if release_row else None,
                )
                session.add(collection_new)
            else:
                existing_col.doi = col_data["doi"]
                existing_col.title = col_data.get("title")
                existing_col.collection_type = col_data["collection_type"]
                existing_col.size_tib = col_data.get("size_tib")
                existing_col.file_count = col_data.get("file_count")
                existing_col.event_count = col_data.get("event_count")
            counts["collections"] += 1

    session.flush()

    # ---- Datasets ----
    for ds_data in data.get("datasets", []):
        existing_ds = session.query(Dataset).filter_by(dsid=ds_data["dsid"]).first()
        parent_col = (
            session.query(Collection)
            .filter_by(record_id=str(ds_data.get("collection_record_id", "")))
            .first()
        )
        if existing_ds is None or force:
            if existing_ds is None:
                dataset_new = Dataset(
                    dsid=ds_data["dsid"],
                    name=ds_data.get("name"),
                    process_type=ds_data.get("process_type"),
                    cross_section=ds_data.get("cross_section"),
                    filter_efficiency=ds_data.get("filter_efficiency"),
                    k_factor=ds_data.get("k_factor"),
                    collection_id=parent_col.id if parent_col else None,
                )
                session.add(dataset_new)
            else:
                existing_ds.name = ds_data.get("name")
                existing_ds.cross_section = ds_data.get("cross_section")
                existing_ds.filter_efficiency = ds_data.get("filter_efficiency")
                existing_ds.k_factor = ds_data.get("k_factor")
            counts["datasets"] += 1

    session.commit()
    return counts


def run(db_path: str | None = None) -> dict[str, int]:
    """Convenience wrapper for CLI use: creates its own session."""
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from atlas_workbench.db.models import Base

    url = db_path or os.environ.get("DATABASE_URL", "sqlite:///./atlas_workbench.db")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        return seed(session)
