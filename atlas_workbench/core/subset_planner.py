"""Deterministic subset planner — algorithm v0.1 (hash sampling).

Algorithm
---------
1. Strip simplecache:: prefix from every URL (canonical key).
2. Compute sha256(key.encode('utf-8')).hexdigest() for each key.
3. Sort by (sha256_hex, canonical_url) — deterministic, order-independent.
4. Select the first N entries.
5. Compute a plan_hash as sha256 over the sorted selected URLs.

N defaults
----------
* collection_type == 'collision'  → N = 3
* collection_type == 'mc'         → N = 1
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field

ALGORITHM_VERSION: str = "v0.1"
HASHING_METHOD: str = "sha256"

N_COLLISION: int = 3
N_MC: int = 1

_SIMPLECACHE_PREFIX = "simplecache::"


def _canonical(url: str) -> str:
    if url.startswith(_SIMPLECACHE_PREFIX):
        return url[len(_SIMPLECACHE_PREFIX) :]
    return url


def _file_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


@dataclass
class SubsetPlan:
    plan_id: str
    algorithm_version: str
    hashing_method: str
    collection_type: str
    n: int
    selected_files: list[str]
    plan_hash: str
    total_size_bytes: int = 0
    dataset_ref: str = ""
    extra_fields: dict = field(default_factory=dict)


def select_subset(
    urls: list[str],
    collection_type: str,
    n: int | None = None,
    dataset_ref: str = "",
) -> SubsetPlan:
    """Select a deterministic subset of N files from a URL list.

    Parameters
    ----------
    urls:
        Raw URL list (may contain simplecache:: prefixes).
    collection_type:
        'collision' or 'mc' — determines default N.
    n:
        Override for N; if None, uses default for collection_type.
    dataset_ref:
        Optional label stored on the plan for traceability.
    """
    if n is None:
        n = N_MC if collection_type == "mc" else N_COLLISION

    # Deduplicate while preserving hash-sort order
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        key = _canonical(url)
        if key not in seen:
            seen.add(key)
            unique_urls.append(key)

    # Sort deterministically: (sha256_hex, canonical_url)
    sorted_urls = sorted(unique_urls, key=lambda u: (_file_hash(u), u))

    selected = sorted_urls[:n]

    # Plan hash over selected ordered list
    h = hashlib.sha256()
    for url in selected:
        h.update(url.encode("utf-8"))
        h.update(b"\n")
    plan_hash = h.hexdigest()

    return SubsetPlan(
        plan_id=str(uuid.uuid4()),
        algorithm_version=ALGORITHM_VERSION,
        hashing_method=HASHING_METHOD,
        collection_type=collection_type,
        n=n,
        selected_files=selected,
        plan_hash=plan_hash,
        dataset_ref=dataset_ref,
    )
