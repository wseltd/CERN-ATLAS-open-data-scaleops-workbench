"""Unit tests for manifest_builder URL normalisation and hash stability."""

from atlas_workbench.core.manifest_builder import (
    _root_to_https,
    compute_manifest_hash,
    normalize_url,
)


def test_normalize_url_strips_simplecache_prefix():
    url = "simplecache::root://eospublic.cern.ch//eos/opendata/atlas/file.root"
    assert normalize_url(url) == "root://eospublic.cern.ch//eos/opendata/atlas/file.root"


def test_normalize_url_preserves_double_slash():
    url = "root://eospublic.cern.ch//eos/opendata/atlas/file.root"
    assert normalize_url(url) == url


def test_normalize_url_adds_double_slash_when_missing():
    # Single slash after hostname should be corrected
    url = "root://eospublic.cern.ch/eos/opendata/atlas/file.root"
    result = normalize_url(url)
    assert result == "root://eospublic.cern.ch//eos/opendata/atlas/file.root"


def test_normalize_url_preserves_port_in_root_url():
    # atlasopenmagic returns URLs with :1094 — must be preserved, not stripped
    url = "root://eospublic.cern.ch:1094//eos/opendata/atlas/file.root"
    assert normalize_url(url) == url


def test_root_to_https_with_port():
    url = "root://eospublic.cern.ch:1094//eos/opendata/atlas/file.root"
    result = _root_to_https(url)
    assert result == "http://opendata.cern.ch/eos/opendata/atlas/file.root"


def test_root_to_https_without_port():
    url = "root://eospublic.cern.ch//eos/opendata/atlas/file.root"
    result = _root_to_https(url)
    assert result == "http://opendata.cern.ch/eos/opendata/atlas/file.root"


def test_root_to_https_unknown_host_returns_none():
    url = "root://other.server.cern.ch//eos/opendata/atlas/file.root"
    assert _root_to_https(url) is None


def test_normalize_url_https_passthrough():
    url = "http://opendata.cern.ch/eos/opendata/atlas/file.root"
    assert normalize_url(url) == url


def test_compute_manifest_hash_is_reproducible():
    urls = [
        "root://eospublic.cern.ch//eos/opendata/atlas/a.root",
        "root://eospublic.cern.ch//eos/opendata/atlas/b.root",
    ]
    h1 = compute_manifest_hash(urls)
    h2 = compute_manifest_hash(urls)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex digest


def test_compute_manifest_hash_empty_list():
    h = compute_manifest_hash([])
    assert len(h) == 64
    assert h == compute_manifest_hash([])  # stable for empty list
