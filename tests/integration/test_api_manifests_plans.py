"""Integration tests: POST /manifests/build, POST /plans/subset, POST /plans/execution.

Uses a pre-seeded stub manifest — does NOT call atlasopenmagic live.
"""

from __future__ import annotations

import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_workbench.api.main import create_app
from atlas_workbench.db.models import Base
from atlas_workbench.db.session import get_session

_STUB_MC_URLS = [
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/410470/file_001.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/410470/file_002.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/410470/file_003.root",
]
_STUB_COLLISION_URLS = [
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16/file_001.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16/file_002.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/data16/file_003.root",
]


@pytest.fixture
def client():
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


def test_manifests_build_returns_stable_hash(client):
    with patch(
        "atlas_workbench.core.manifest_builder.get_urls",
        return_value=_STUB_MC_URLS,
    ):
        resp = client.post(
            "/manifests/build",
            json={"collection_id": "dsid:410470", "protocol": "root"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "stable_hash" in body
    h = body["stable_hash"]
    assert len(h) == 64
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


def test_plans_subset_mc_returns_algorithm_v0_1_and_n_1(client):
    with patch(
        "atlas_workbench.core.manifest_builder.get_urls",
        return_value=_STUB_MC_URLS,
    ):
        manifest_resp = client.post(
            "/manifests/build",
            json={"collection_id": "dsid:410470", "protocol": "root"},
        )
    manifest_id = manifest_resp.json()["manifest_id"]

    resp = client.post("/plans/subset", json={"manifest_id": manifest_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["algorithm_version"] == "v0.1"
    assert body["n"] == 1  # MC default
    assert len(body["selected_files"]) == 1


def test_plans_execution_returns_pinned_container_image(client):
    with patch(
        "atlas_workbench.core.manifest_builder.get_file_locations",
        return_value=_STUB_COLLISION_URLS,
    ):
        manifest_resp = client.post(
            "/manifests/build",
            json={"collection_id": "record:80001", "protocol": "root"},
        )
    manifest_id = manifest_resp.json()["manifest_id"]
    subset_resp = client.post("/plans/subset", json={"manifest_id": manifest_id})
    subset_plan_id = subset_resp.json()["plan_id"]

    resp = client.post("/plans/execution", json={"subset_plan_id": subset_plan_id})
    assert resp.status_code == 200
    body = resp.json()
    assert "25.2.2" in body["container_image_tag"]
    assert "latest" not in body["container_image_tag"].lower()
    assert body["pinned_packages"]["uproot"] == "5.3.0"
