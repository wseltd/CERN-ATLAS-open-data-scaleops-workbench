"""Unit tests for build_provenance."""

from atlas_workbench.core.provenance import build_provenance


def test_dois_contains_required_records():
    prov = build_provenance(["release", "collision_2016", "mc_top_nominal"])
    assert prov.dois["80020"] == "10.7483/OPENDATA.ATLAS.9HK7.P5SI"
    assert prov.dois["80001"] == "10.7483/OPENDATA.ATLAS.4ZES.DJHA"
    assert prov.dois["80017"] == "10.7483/OPENDATA.ATLAS.MM1Y.O0PH"


def test_release_always_included():
    # Even if only 'collision_2016' is requested, release is always included
    prov = build_provenance(["collision_2016"])
    assert 80020 in prov.record_ids


def test_license_is_cc0():
    prov = build_provenance(["release"])
    assert "CC0" in prov.license
