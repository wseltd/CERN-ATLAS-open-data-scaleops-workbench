"""Docs corpus seeder: fetches 7 official ATLAS/CERN documentation pages and stores them."""

from __future__ import annotations

import re
import urllib.request
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from atlas_workbench.db.models import DocPage

DOCS_URLS: list[str] = [
    "https://opendata.cern.ch/docs/atlas-open-data-for-research-release-2024",
    "https://opendata.atlas.cern/docs/data/access_data",
    "https://opendata.atlas.cern/docs/data/atlasopenmagic",
    "https://opendata.atlas.cern/docs/data/cernopendata_client",
    "https://opendata.atlas.cern/docs/tutresearch/physlitetut/",
    "https://opendata.atlas.cern/docs/tutresearch/containers/",
    "https://opendata.atlas.cern/docs/documentation/ethical_legal/citation_policy/",
]

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s{3,}")


def _fetch_page(url: str) -> tuple[str, str]:
    """Fetch a URL and return (title, stripped_text).  Best-effort — no retries."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "atlas-scaleops-workbench/0.1 (docs-seed)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310  # nosec B310
        raw = resp.read().decode("utf-8", errors="replace")

    # Extract <title>
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else url

    # Strip tags, collapse whitespace
    text = _TAG_RE.sub(" ", raw)
    text = _WHITESPACE_RE.sub("  ", text).strip()

    return title, text


def seed(session: Session, force: bool = False) -> int:
    """Fetch and upsert all documentation pages.  Returns count of pages stored."""
    stored = 0
    for url in DOCS_URLS:
        existing = session.query(DocPage).filter_by(url=url).first()
        if existing is not None and not force:
            continue
        try:
            title, content_text = _fetch_page(url)
        except Exception as exc:
            # Log and continue — a missing doc page should not abort the seed
            title = f"[fetch-error] {url}"
            content_text = f"Failed to fetch: {exc}"

        now = datetime.now(tz=timezone.utc)
        if existing is None:
            page = DocPage(url=url, title=title, content_text=content_text, fetched_at=now)
            session.add(page)
        else:
            existing.title = title
            existing.content_text = content_text
            existing.fetched_at = now
        stored += 1

    session.commit()
    return stored


def run(db_path: str | None = None) -> int:
    """Convenience wrapper for CLI use."""
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
