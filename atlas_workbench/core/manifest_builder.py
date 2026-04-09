"""File manifest builder.

Builds a FileManifest for a dataset reference by calling atlas_client first,
falling back to cern_client on empty result or exception.

URL normalisation rules (applied to every URL before storage and hashing):
  1. Strip the 'simplecache::' prefix.
  2. Ensure root:// URLs preserve the double-slash after the hostname:
       root://eospublic.cern.ch//eos/... (the // before /eos is required).
  3. Derive the https:// equivalent by rewriting the scheme and host:
       root://eospublic.cern.ch//eos/opendata/...
       → http://opendata.cern.ch/eos/opendata/...
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from atlas_workbench.core.atlas_client import AtlasClientError, get_urls
from atlas_workbench.core.cern_client import CernClientError, get_file_locations


@dataclass
class FileEntry:
    dataset_ref: str
    file_url_root: str
    file_url_https: str | None
    size_bytes: int | None
    source_tool: str
    discovered_at: datetime


@dataclass
class ManifestResult:
    dataset_ref: str
    release_tag: str
    protocol: str
    file_count: int
    stable_hash: str
    files: list[FileEntry] = field(default_factory=list)


_SIMPLECACHE_PREFIX = "simplecache::"


def normalize_url(url: str) -> str:
    """Normalize a raw URL to canonical root:// form.

    Strips simplecache prefix and ensures double-slash is present after
    the xrootd hostname.
    """
    if url.startswith(_SIMPLECACHE_PREFIX):
        url = url[len(_SIMPLECACHE_PREFIX) :]
    # Ensure double-slash in root:// URLs: root://host/path → root://host//path
    if url.startswith("root://"):
        # Split after "root://hostname"
        after_scheme = url[len("root://") :]
        slash_idx = after_scheme.find("/")
        if slash_idx != -1:
            host = after_scheme[:slash_idx]
            path = after_scheme[slash_idx:]
            if not path.startswith("//"):
                path = "/" + path
            url = f"root://{host}{path}"
    return url


def _root_to_https(root_url: str) -> str | None:
    """Derive an https URL from a root:// URL.

    root://eospublic.cern.ch//eos/opendata/...
    → http://opendata.cern.ch/eos/opendata/...

    Returns None if the URL is not a recognised root:// form.
    """
    if not root_url.startswith("root://eospublic.cern.ch//"):
        return None
    path = root_url[len("root://eospublic.cern.ch/") :]
    return f"http://opendata.cern.ch{path}"


def compute_manifest_hash(urls: list[str]) -> str:
    """Compute a stable SHA-256 hex digest over an ordered list of canonical URLs."""
    h = hashlib.sha256()
    for url in urls:
        h.update(url.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def build_manifest(
    dataset_ref: str,
    release_tag: str = "2024r-pp",
    protocol: str = "root",
) -> ManifestResult:
    """Build a file manifest for a dataset reference.

    Parameters
    ----------
    dataset_ref:
        Either 'dsid:<int>' (e.g. 'dsid:410470') or 'record:<str>'
        (e.g. 'record:80001').
    release_tag:
        Release tag passed to atlasopenmagic (default: '2024r-pp').
    protocol:
        'root' or 'https'.
    """
    raw_urls: list[str] = []
    source_tool: str

    # Prefer atlasopenmagic for DSID-based refs; fall back to cern_client for records
    if dataset_ref.startswith("dsid:"):
        dsid = int(dataset_ref[len("dsid:") :])
        try:
            raw_urls = get_urls(dsid=dsid, release_tag=release_tag, protocol=protocol)
            source_tool = "atlasopenmagic"
        except AtlasClientError:
            raw_urls = []
            source_tool = "atlasopenmagic-failed"
    else:
        source_tool = "cernopendata-client"

    if not raw_urls:
        record_id_str = (
            dataset_ref[len("record:") :] if dataset_ref.startswith("record:") else dataset_ref
        )
        try:
            record_id = int(record_id_str)
            raw_urls = get_file_locations(record_id=record_id, protocol=protocol)
            source_tool = "cernopendata-client"
        except (CernClientError, ValueError) as exc:
            raise RuntimeError(
                f"Could not retrieve URLs for dataset_ref={dataset_ref!r}: {exc}"
            ) from exc

    now = datetime.now(tz=timezone.utc)
    canonical_urls: list[str] = [normalize_url(u) for u in raw_urls]

    files: list[FileEntry] = [
        FileEntry(
            dataset_ref=dataset_ref,
            file_url_root=u,
            file_url_https=_root_to_https(u),
            size_bytes=None,
            source_tool=source_tool,
            discovered_at=now,
        )
        for u in canonical_urls
    ]

    stable_hash = compute_manifest_hash(canonical_urls)

    return ManifestResult(
        dataset_ref=dataset_ref,
        release_tag=release_tag,
        protocol=protocol,
        file_count=len(files),
        stable_hash=stable_hash,
        files=files,
    )
