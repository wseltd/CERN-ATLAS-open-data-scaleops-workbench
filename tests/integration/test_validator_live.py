"""Network-gated live validation tests against CERN Open Data xrootd endpoints.

Both tests are marked xfail(strict=False): they pass when xrootd is reachable
and the data is accessible, and are treated as expected-skipped when the network
is unavailable. CI without CERN network access will see these as xfailed, not failures.
"""

from __future__ import annotations

import socket

import pytest

from atlas_workbench.core.subset_planner import select_subset
from atlas_workbench.core.validator import (
    COLLECTION_TREE,
    DSID_TTBAR,
    RELEASE_TAG,
    run_validation,
)


def check_xrootd_reachable() -> bool:
    try:
        socket.create_connection(("eospublic.cern.ch", 1094), timeout=5)
        return True
    except OSError:
        return False


@pytest.mark.xfail(strict=False, reason="xrootd network unavailable")
def test_live_ttbar_mc_collection_tree_numentries():
    """Open a real ttbar PHYSLITE file and confirm CollectionTree has entries."""
    if not check_xrootd_reachable():
        pytest.skip("eospublic.cern.ch:1094 unreachable")

    from atlas_workbench.core.atlas_client import get_urls

    urls = get_urls(dsid=DSID_TTBAR, release_tag=RELEASE_TAG, protocol="root")
    plan = select_subset(urls=urls, collection_type="mc", n=1, dataset_ref=f"dsid:{DSID_TTBAR}")

    report = run_validation(plan, protocol="root")
    assert report.success, f"Validation failed: {report.error_logs}"
    assert report.numentries_mc is not None
    assert report.numentries_mc > 0, "CollectionTree numentries must be > 0"


@pytest.mark.xfail(strict=False, reason="xrootd network unavailable")
def test_live_collision_2016_collection_tree_exists():
    """Open a real collision 2016 PHYSLITE file and confirm CollectionTree exists."""
    if not check_xrootd_reachable():
        pytest.skip("eospublic.cern.ch:1094 unreachable")

    from atlas_workbench.core.cern_client import get_file_locations

    urls = get_file_locations(record_id=80001, protocol="root")
    plan = select_subset(
        urls=urls[:5], collection_type="collision", n=1, dataset_ref="record:80001"
    )

    import uproot  # type: ignore[import]

    url = plan.selected_files[0]
    with uproot.open(url) as f:
        assert COLLECTION_TREE in f, f"CollectionTree not found in {url}"
        tree = f[COLLECTION_TREE]
        assert tree.num_entries > 0
