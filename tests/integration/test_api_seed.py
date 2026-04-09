"""Integration tests: GET /health, POST /seed, GET /collections."""

from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_workbench.api.main import create_app
from atlas_workbench.db.models import Base
from atlas_workbench.db.session import get_session


@pytest.fixture
def client():
    """TestClient backed by a fresh in-memory SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_url = f"sqlite:///{tmp.name}"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)

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


def test_health_endpoint_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_seed_endpoint_returns_200_and_collection_count_matches_fixtures(client):
    resp = client.post("/seed", json={"force": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # Fixture has 3 collections (80001, 80000, 80017)
    assert body["collections_seeded"] == 3


def test_collections_endpoint_returns_seeded_record_ids(client):
    client.post("/seed", json={"force": False})
    resp = client.get("/collections")
    assert resp.status_code == 200
    record_ids = {c["record_id"] for c in resp.json()}
    assert "80001" in record_ids
    assert "80000" in record_ids
    assert "80017" in record_ids
