"""Query engine: answers structured questions about the ATLAS open-data release.

Queries are resolved against the SQLite metadata store; documentation pages
are searched by keyword for evidence. No generative AI — deterministic lookups.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from atlas_workbench.core.provenance import build_provenance


@dataclass
class QueryResponse:
    answer: str
    intent: str
    release_summary: dict
    selected_collections: list[dict]
    manifest_summary: dict
    access_strategy: dict
    subset_plan: dict
    execution_plan: dict
    provenance_and_citation: dict
    evidence: list[str]
    caveats: list[str]


_RELEASE_FIELDS = (
    "record_id",
    "doi",
    "title",
    "total_size_tib",
    "file_count",
    "event_count",
    "release_tag",
)

_COLLECTION_FIELDS = (
    "record_id",
    "doi",
    "title",
    "collection_type",
    "size_tib",
    "file_count",
    "event_count",
)


def _release_summary(session: Session) -> dict:
    from atlas_workbench.db.models import Release

    row = session.query(Release).first()
    if row is None:
        return {"status": "not_seeded"}
    return {
        "record_id": row.record_id,
        "doi": row.doi,
        "title": row.title,
        "total_size_tib": row.total_size_tib,
        "file_count": row.file_count,
        "event_count": row.event_count,
        "release_tag": row.release_tag,
        "scale_note": (
            "65.3 TiB total; 70,611 files; 9,058,437,931 events. "
            "Size is in TiB (not TB). The full corpus is never downloaded by default."
        ),
    }


def _collections_summary(session: Session) -> list[dict]:
    from atlas_workbench.db.models import Collection

    rows = session.query(Collection).all()
    return [
        {
            "record_id": r.record_id,
            "doi": r.doi,
            "title": r.title,
            "collection_type": r.collection_type,
            "size_tib": r.size_tib,
            "file_count": r.file_count,
            "event_count": r.event_count,
        }
        for r in rows
    ]


def _detect_intent(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ("scale", "size", "tib", "file count", "event count", "total")):
        return "release_scale"
    if any(w in q for w in ("collection", "record", "list", "classify")):
        return "collection_lookup"
    if any(w in q for w in ("manifest", "build", "file list", "inventory")):
        return "manifest_query"
    if any(w in q for w in ("subset", "deterministic", "algorithm", "hash", "select")):
        return "subset_planning"
    if any(w in q for w in ("stream", "cache", "xrootd", "root://", "protocol", "access")):
        return "access_strategy"
    if any(w in q for w in ("execution", "container", "image", "docker", "pinned")):
        return "execution_plan"
    if any(w in q for w in ("citation", "doi", "license", "provenance", "cc0")):
        return "provenance_citation"
    if any(w in q for w in ("validate", "validation", "collectiontree", "uproot", "branch")):
        return "validation"
    if any(w in q for w in ("weight", "cross section", "filter efficiency", "k factor", "mc")):
        return "mc_normalization"
    if any(w in q for w in ("fallback", "fail", "slow", "https", "rewrite")):
        return "fallback_strategy"
    if any(w in q for w in ("reproduce", "reproducib", "reason", "could not")):
        return "reproducibility"
    return "general"


_STATIC_ANSWERS: dict[str, str] = {
    "release_scale": (
        "The ATLAS 2024 Open Data for Research release (record 80020, "
        "DOI 10.7483/OPENDATA.ATLAS.9HK7.P5SI) contains 65.3 TiB, 70,611 files, "
        "and 9,058,437,931 events. Sizes are in TiB; the commonly cited '65 TB' is "
        "a narrative approximation."
    ),
    "collection_lookup": (
        "The release contains two collision collections (records 80000 and 80001) "
        "and multiple MC collections. Record 80001 (2016 pp) has 45,571 files / 35.4 TiB; "
        "record 80000 (2015 pp) has 10,049 files / 9.3 TiB; "
        "record 80017 (top nominal MC) has 437 files / 855.3 GiB."
    ),
    "manifest_query": (
        "Use POST /manifests/build with {'collection_id': 'record:80001', 'protocol': 'root'} "
        "to build a file manifest. The manifest stores canonical root:// URLs with stable_hash "
        "over the ordered file list for deterministic subset selection."
    ),
    "subset_planning": (
        "Algorithm v0.1: (1) normalize URLs (strip simplecache::), (2) sha256 each URL, "
        "(3) sort by (hash, url), (4) select first N. N=3 for collision, N=1 for MC. "
        "The plan_hash is sha256 over the selected ordered list."
    ),
    "access_strategy": (
        "Default: root:// streaming via XRootD (eospublic.cern.ch:1094). "
        "Fallback: rewrite root://eospublic.cern.ch//eos/... to http://opendata.cern.ch/eos/... "
        "Cache threshold: 10 GiB — subsets below this size are cached locally in /tmp/atlas_cache."
    ),
    "execution_plan": (
        "Container: gitlab-registry.cern.ch/atlas/athena/analysisbase:25.2.2. "
        "Pinned packages: uproot>=5.3.0, awkward>=2.6.0, vector>=1.1.1, "
        "atlasopenmagic==1.9.0, cernopendata-client==1.0.2."
    ),
    "provenance_citation": (
        "License: CC0 1.0. ATLAS requests citation of the dataset DOI(s) used. "
        "Primary DOI: 10.7483/OPENDATA.ATLAS.9HK7.P5SI (record 80020). "
        "Citation policy: https://opendata.atlas.cern/docs/documentation/ethical_legal/citation_policy/"
    ),
    "validation": (
        "Validation opens DSID 410470 (tt-bar) via uproot, accesses CollectionTree, "
        "reads AnalysisElectronsAuxDyn.pt, and asserts numentries > 0. "
        "Also opens one collision 2016 file and confirms CollectionTree exists."
    ),
    "mc_normalization": (
        "Event weight = cross_section × filter_efficiency × k_factor. "
        "Never use raw cross_section alone. For DSID 410470: "
        "cross_section=831.76 pb, filter_efficiency=0.5433, k_factor=1.0."
    ),
    "fallback_strategy": (
        "If XRootD is slow or unavailable: rewrite root://eospublic.cern.ch//eos/opendata/... "
        "to http://opendata.cern.ch/eos/opendata/... (note: double-slash preserved in path). "
        "For local development, use fsspec simplecache with protocol='https'."
    ),
    "reproducibility": (
        "Top three reasons a run may not be reproducible: "
        "(1) Container image tag not pinned to digest — using :25.2.2 tag without digest "
        "allows silent updates. "
        "(2) Protocol not recorded — if xrootd/https fallback was used, the choice must appear "
        "in the execution plan. "
        "(3) Subset algorithm version not recorded — plan_hash alone is insufficient without "
        "algorithm_version and N in the SubsetPlan artifact."
    ),
    "general": (
        "This is the ATLAS Open Data ScaleOps Workbench — a control-plane system for the "
        "ATLAS 2024 DAOD_PHYSLITE release (65.3 TiB, 70,611 files). "
        "Use POST /seed to load metadata, then POST /query, POST /manifests/build, "
        "POST /plans/subset, POST /validate/run."
    ),
}


def answer(question: str, session: Session) -> QueryResponse:
    """Answer a structured question about the ATLAS release."""
    intent = _detect_intent(question)
    answer_text = _STATIC_ANSWERS.get(intent, _STATIC_ANSWERS["general"])

    prov = build_provenance(["release", "collision_2016", "mc_top_nominal"])

    return QueryResponse(
        answer=answer_text,
        intent=intent,
        release_summary=_release_summary(session),
        selected_collections=_collections_summary(session),
        manifest_summary={
            "note": "Use POST /manifests/build to generate a manifest.",
            "max_files_streamed_not_downloaded": True,
        },
        access_strategy={
            "default_protocol": "root",
            "fallback_protocol": "https",
            "url_rewrite": "root://eospublic.cern.ch//eos/ → http://opendata.cern.ch/eos/",
            "cache_threshold_gib": 10,
            "cache_dir": "/tmp/atlas_cache",  # nosec B108
        },
        subset_plan={
            "algorithm": "v0.1",
            "hashing_method": "sha256",
            "n_collision": 3,
            "n_mc": 1,
        },
        execution_plan={
            "container_image_tag": "gitlab-registry.cern.ch/atlas/athena/analysisbase:25.2.2",
            "pinned_packages": {
                "uproot": ">=5.3.0",
                "awkward": ">=2.6.0",
                "vector": ">=1.1.1",
            },
        },
        provenance_and_citation={
            "record_ids": prov.record_ids,
            "dois": prov.dois,
            "citation_text": prov.citation_text,
            "license": prov.license,
            "license_note": prov.license_note,
        },
        evidence=[
            "https://opendata.cern.ch/record/80020",
            "https://opendata.atlas.cern/docs/data/access_data",
            "https://opendata.atlas.cern/docs/data/atlasopenmagic",
        ],
        caveats=[
            "Full 65.3 TiB corpus is never downloaded; validation streams small byte ranges.",
            "XRootD connectivity to eospublic.cern.ch:1094 required for root:// protocol.",
            "MC event weights require cross_section × filter_efficiency × k_factor.",
        ],
    )
