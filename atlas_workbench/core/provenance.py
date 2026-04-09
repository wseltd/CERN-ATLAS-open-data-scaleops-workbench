"""Provenance and citation builder.

Assembles a ProvenanceRecord entirely from frozen module-level constants.
Zero network calls, zero database reads.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---- Frozen catalogue -----------------------------------------------------------
ATLAS_RECORD_IDS: dict[str, int] = {
    "release": 80020,
    "collision_2016": 80001,
    "collision_2015": 80000,
    "mc_top_nominal": 80017,
}

ATLAS_DOIS: dict[str, str] = {
    "release": "10.7483/OPENDATA.ATLAS.9HK7.P5SI",
    "collision_2016": "10.7483/OPENDATA.ATLAS.4ZES.DJHA",
    "collision_2015": "10.7483/OPENDATA.ATLAS.AOQL.8TT3",
    "mc_top_nominal": "10.7483/OPENDATA.ATLAS.MM1Y.O0PH",
}

LICENSE: str = "CC0 1.0 Universal (CC0 1.0) Public Domain Dedication"

CITATION_TEMPLATE: str = (
    "ATLAS Collaboration (2024). ATLAS Open Data for Research (DAOD_PHYSLITE, Run 2). "
    "CERN Open Data Portal. DOI: {dois}"
)

CITATION_POLICY_URL: str = (
    "https://opendata.atlas.cern/docs/documentation/ethical_legal/citation_policy/"
)

LICENSE_NOTE: str = (
    "Data are released under CC0 1.0. ATLAS requests — but does not legally require — "
    "that users cite the dataset DOI(s) used and follow the citation policy at "
    f"{CITATION_POLICY_URL}"
)


@dataclass
class ProvenanceRecord:
    record_ids: list[int]
    dois: dict[str, str]
    citation_text: str
    license: str
    license_note: str
    citation_policy_url: str


def build_provenance(dataset_refs: list[str]) -> ProvenanceRecord:
    """Build a ProvenanceRecord for the given dataset reference keys.

    Parameters
    ----------
    dataset_refs:
        Keys from ATLAS_RECORD_IDS (e.g. ['release', 'collision_2016']).
        Unknown keys are silently ignored so callers can pass broad lists.

    Returns
    -------
    ProvenanceRecord
        Always includes the top-level release record (80020) regardless of
        which dataset_refs are passed, because every run derives from the
        overall release.
    """
    # Always include the top-level release
    keys = list({"release"} | {r for r in dataset_refs if r in ATLAS_RECORD_IDS})
    keys.sort()  # deterministic ordering

    record_ids = [ATLAS_RECORD_IDS[k] for k in keys]
    dois = {str(ATLAS_RECORD_IDS[k]): ATLAS_DOIS[k] for k in keys}

    doi_list = ", ".join(sorted(dois.values()))
    citation_text = CITATION_TEMPLATE.format(dois=doi_list)

    return ProvenanceRecord(
        record_ids=record_ids,
        dois=dois,
        citation_text=citation_text,
        license=LICENSE,
        license_note=LICENSE_NOTE,
        citation_policy_url=CITATION_POLICY_URL,
    )
