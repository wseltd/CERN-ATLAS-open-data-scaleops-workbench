"""Unit tests for build_execution_plan."""

from atlas_workbench.core.execution_planner import (
    CONTAINER_IMAGE_TAG,
    build_execution_plan,
)
from atlas_workbench.core.stream_decision import decide_stream_vs_cache

_SMALL_FILES = [
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/file_001.root",
]
_LARGE_BYTES = 20 * 1024 * 1024 * 1024  # 20 GiB


def test_container_image_tag_is_exact():
    sd = decide_stream_vs_cache(1024)
    plan = build_execution_plan(selected_files=_SMALL_FILES, stream_decision=sd)
    assert plan.container_image_tag == CONTAINER_IMAGE_TAG
    assert "25.2.2" in plan.container_image_tag
    assert "latest" not in plan.container_image_tag.lower()


def test_pinned_packages_contains_uproot_awkward_vector():
    sd = decide_stream_vs_cache(1024)
    plan = build_execution_plan(selected_files=_SMALL_FILES, stream_decision=sd)
    assert plan.pinned_packages["uproot"] == "5.3.0"
    assert plan.pinned_packages["awkward"] == "2.6.0"
    assert plan.pinned_packages["vector"] == "1.1.1"


def test_mc_weight_fields_present():
    sd = decide_stream_vs_cache(1024)
    plan = build_execution_plan(selected_files=_SMALL_FILES, stream_decision=sd)
    assert "cross_section" in plan.mc_weight_fields
    assert "filter_efficiency" in plan.mc_weight_fields
    assert "k_factor" in plan.mc_weight_fields
