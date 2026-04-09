"""Integration tests: POST /query response schema and field presence."""

from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_workbench.api.main import create_app
from atlas_workbench.core import metadata_seeder
from atlas_workbench.db.models import Base
from atlas_workbench.db.session import get_session

_REQUIRED_FIELDS = {
    "answer",
    "intent",
    "release_summary",
    "selected_collections",
    "manifest_summary",
    "access_strategy",
    "subset_plan",
    "execution_plan",
    "provenance_and_citation",
    "evidence",
    "caveats",
}


@pytest.fixture(scope="module")
def seeded_client():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_url = f"sqlite:///{tmp.name}"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)

        # Pre-seed directly (not via HTTP endpoint) for test isolation
        with TestSession() as session:
            metadata_seeder.seed(session)

        def override_session():
            session = TestSession()
            try:
                yield session
            finally:
                session.close()

        app = create_app()
        app.dependency_overrides[get_session] = override_session

        with TestClient(app) as c:
            yield c


def test_query_response_has_all_required_fields(seeded_client):
    resp = seeded_client.post(
        "/query", json={"question": "What is the record ID for the top-level ATLAS release?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    missing = _REQUIRED_FIELDS - set(body.keys())
    assert not missing, f"Response missing fields: {missing}"


def test_query_intent_non_empty(seeded_client):
    resp = seeded_client.post(
        "/query", json={"question": "What is the total size of the ATLAS release in TiB?"}
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] != ""


def test_query_provenance_contains_doi(seeded_client):
    resp = seeded_client.post("/query", json={"question": "What is the citation DOI?"})
    assert resp.status_code == 200
    prov = resp.json()["provenance_and_citation"]
    assert "80020" in prov.get("dois", {})


def test_query_caveats_present(seeded_client):
    resp = seeded_client.post("/query", json={"question": "How do I access the data?"})
    assert resp.status_code == 200
    assert len(resp.json()["caveats"]) > 0
