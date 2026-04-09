"""Uproot remote validator.

Validates against live ATLAS Open Data via xrootd (or https fallback).

Two sequential sub-tasks per run:
  1. Open DSID 410470 (tt-bar MC) file, read AnalysisElectronsAuxDyn.pt,
     assert CollectionTree exists and numentries > 0.
  2. Open one collision 2016 file, assert CollectionTree exists.

All bytes_read and wall_time are recorded.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field

from atlas_workbench.core.subset_planner import SubsetPlan

DSID_TTBAR: int = 410470
RELEASE_TAG: str = "2024r-pp"
COLLECTION_TREE: str = "CollectionTree"
BRANCH_ELECTRONS_PT: str = "AnalysisElectronsAuxDyn.pt"


@dataclass
class ValidationReport:
    success: bool
    error_logs: list[str]
    bytes_read: int
    wall_time: float
    numentries_mc: int | None
    numentries_collision: int | None
    branches_read: list[str] = field(default_factory=list)
    summary_metrics: dict = field(default_factory=dict)


def xrootd_reachable(
    host: str = "eospublic.cern.ch", port: int = 1094, timeout: float = 5.0
) -> bool:
    """Return True if the xrootd endpoint is reachable."""
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except OSError:
        return False


def _open_and_read(url: str, protocol_fallback: bool = True) -> tuple[int, int, list[str]]:
    """Open a PHYSLITE ROOT file, read CollectionTree.

    Returns (numentries, bytes_read, branches_read).
    Raises RuntimeError on failure.

    When xrootd (port 1094) is unreachable, skips directly to the http://
    fallback URL rather than waiting for a 60-second connection timeout.
    """
    import uproot  # type: ignore[import]

    _xrootd_up = xrootd_reachable()
    errors = []
    for attempt_url in _url_variants(url):
        if attempt_url.startswith("root://") and not _xrootd_up:
            errors.append(f"{attempt_url}: skipped (xrootd port 1094 unreachable)")
            continue
        try:
            with uproot.open(attempt_url) as f:
                tree = f[COLLECTION_TREE]
                numentries: int = tree.num_entries
                branches_read: list[str] = []
                bytes_read = 0
                # Read the electrons pT branch if present
                if BRANCH_ELECTRONS_PT in tree.keys():
                    arr = tree[BRANCH_ELECTRONS_PT].array(entry_stop=min(numentries, 100))
                    bytes_read = arr.nbytes if hasattr(arr, "nbytes") else 0
                    branches_read.append(BRANCH_ELECTRONS_PT)
                return numentries, bytes_read, branches_read
        except Exception as exc:
            errors.append(f"{attempt_url}: {exc}")

    raise RuntimeError(f"Could not open {url}: " + "; ".join(errors))


def _url_variants(url: str) -> list[str]:
    """Return [root_url, https_fallback] for a given URL.

    Handles both root://eospublic.cern.ch:1094//... (atlasopenmagic form)
    and root://eospublic.cern.ch//... (port-free form).
    """
    variants = [url]
    for prefix in ("root://eospublic.cern.ch:1094/", "root://eospublic.cern.ch/"):
        if url.startswith(prefix):
            path = url[len(prefix) :]
            if not path.startswith("/"):
                path = "/" + path
            variants.append(f"http://opendata.cern.ch{path}")
            break
    return variants


def run_validation(subset_plan: SubsetPlan, protocol: str = "root") -> ValidationReport:
    """Run the two-step validation against live ATLAS Open Data.

    Parameters
    ----------
    subset_plan:
        Subset plan; MC file URLs are filtered by dsid field if present.
    protocol:
        Preferred access protocol ('root' or 'https').
    """
    errors: list[str] = []
    total_bytes = 0
    total_entries_mc: int | None = None
    total_entries_collision: int | None = None
    all_branches: list[str] = []
    t0 = time.perf_counter()

    mc_files = [u for u in subset_plan.selected_files if "410470" in u]
    collision_files = [u for u in subset_plan.selected_files if "410470" not in u]

    # Also try to retrieve ttbar URL via atlasopenmagic if not in subset_plan
    if not mc_files:
        try:
            from atlas_workbench.core.atlas_client import get_urls

            mc_files = get_urls(dsid=DSID_TTBAR, release_tag=RELEASE_TAG, protocol=protocol)[:1]
        except Exception as exc:
            errors.append(f"atlasopenmagic fallback failed: {exc}")

    # --- Sub-task 1: MC ttbar file ---
    if mc_files:
        try:
            n, b, branches = _open_and_read(mc_files[0])
            total_entries_mc = n
            total_bytes += b
            all_branches.extend(branches)
            if n <= 0:
                errors.append(f"CollectionTree numentries=0 for {mc_files[0]}")
        except Exception as exc:
            errors.append(f"MC validation failed: {exc}")
    else:
        errors.append("No MC ttbar files available in subset plan")

    # --- Sub-task 2: Collision file ---
    if collision_files:
        try:
            n, b, branches = _open_and_read(collision_files[0])
            total_entries_collision = n
            total_bytes += b
            all_branches.extend(b for b in branches if b not in all_branches)
            if n <= 0:
                errors.append(f"CollectionTree numentries=0 for {collision_files[0]}")
        except Exception as exc:
            errors.append(f"Collision validation failed: {exc}")

    wall_time = time.perf_counter() - t0
    success = len(errors) == 0

    return ValidationReport(
        success=success,
        error_logs=errors,
        bytes_read=total_bytes,
        wall_time=wall_time,
        numentries_mc=total_entries_mc,
        numentries_collision=total_entries_collision,
        branches_read=all_branches,
        summary_metrics={
            "mc_files_attempted": len(mc_files),
            "collision_files_attempted": len(collision_files),
        },
    )
