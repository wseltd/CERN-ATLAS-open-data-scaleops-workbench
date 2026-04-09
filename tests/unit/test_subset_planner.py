"""Unit tests for subset_planner determinism and correctness."""

import random

from atlas_workbench.core.subset_planner import select_subset

_URLS = [
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/file_001.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/file_002.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/file_003.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/file_004.root",
    "root://eospublic.cern.ch//eos/opendata/atlas/rucio/mc20_13TeV/file_005.root",
]


def test_hash_sort_determinism_with_shuffled_input():
    shuffled = _URLS[:]
    random.shuffle(shuffled)
    plan1 = select_subset(_URLS, collection_type="collision", n=3)
    plan2 = select_subset(shuffled, collection_type="collision", n=3)
    assert plan1.selected_files == plan2.selected_files


def test_n_defaults_to_3_for_collision():
    plan = select_subset(_URLS, collection_type="collision")
    assert plan.n == 3
    assert len(plan.selected_files) == 3


def test_n_defaults_to_1_for_mc():
    plan = select_subset(_URLS, collection_type="mc")
    assert plan.n == 1
    assert len(plan.selected_files) == 1


def test_plan_hash_stability():
    plan1 = select_subset(_URLS, collection_type="collision", n=2)
    plan2 = select_subset(_URLS, collection_type="collision", n=2)
    assert plan1.plan_hash == plan2.plan_hash
    assert len(plan1.plan_hash) == 64


def test_algorithm_version_field_present():
    plan = select_subset(_URLS, collection_type="mc")
    assert plan.algorithm_version == "v0.1"


def test_n_override():
    plan = select_subset(_URLS, collection_type="collision", n=2)
    assert plan.n == 2
    assert len(plan.selected_files) == 2


def test_duplicate_urls_are_deduplicated():
    urls_with_dupes = _URLS + _URLS  # exact duplicates
    plan = select_subset(urls_with_dupes, collection_type="collision", n=3)
    assert len(plan.selected_files) == 3
    assert len(set(plan.selected_files)) == 3  # all unique
