"""Execution planner: builds a pinned, reproducible execution plan artifact.

Pure builder — zero I/O, zero network, zero subprocess calls.
All version constants are frozen here and never discovered at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from atlas_workbench.core.stream_decision import StreamCacheDecision

# ---- Frozen version pins -------------------------------------------------------
# These must match pyproject.toml and the ATLAS PHYSLITE tutorial pins exactly.
CONTAINER_IMAGE_TAG: str = "gitlab-registry.cern.ch/atlas/athena/analysisbase:25.2.2"

PINNED_PACKAGES: dict[str, str] = {
    "uproot": "5.1.2",
    "awkward": "2.5.0",
    "vector": "1.1.1",
    "atlasopenmagic": "1.9.0",
    "cernopendata-client": "1.0.2",
}

# MC event weight fields — callers must use ALL THREE; raw cross_section alone is wrong.
MC_WEIGHT_FIELDS: list[str] = ["cross_section", "filter_efficiency", "k_factor"]


@dataclass
class ExecutionPlan:
    container_image_tag: str
    command: str
    pinned_packages: dict[str, str]
    env_vars: dict[str, str]
    expected_inputs: list[str]
    expected_outputs: list[str]
    mc_weight_fields: list[str] = field(default_factory=list)
    cache_on: bool = False
    cache_location: str | None = None
    max_cache_size_bytes: int = 0


def build_execution_plan(
    selected_files: list[str],
    stream_decision: StreamCacheDecision,
    dataset_ref: str = "unknown",
) -> ExecutionPlan:
    """Build a pinned execution plan from a file selection and stream decision.

    Parameters
    ----------
    selected_files:
        Canonical file URLs from the subset plan.
    stream_decision:
        Output of decide_stream_vs_cache(); determines cache settings.
    dataset_ref:
        Human-readable label for the dataset (e.g. 'record:80001' or 'dsid:410470').
    """
    env_vars: dict[str, str] = {
        "ATLAS_RELEASE_TAG": "2024r-pp",
        "ATLAS_PROTOCOL": stream_decision.protocol,
    }
    if stream_decision.cache_on and stream_decision.cache_location:
        env_vars["ATLAS_CACHE_DIR"] = stream_decision.cache_location
        env_vars["ATLAS_CACHE_ON"] = "1"

    command = (
        f"python scripts/validate_runner.py "
        f"--dataset-ref {dataset_ref} "
        f"--protocol {stream_decision.protocol}"
    )
    if stream_decision.cache_on and stream_decision.cache_location:
        command += f" --cache-dir {stream_decision.cache_location}"

    return ExecutionPlan(
        container_image_tag=CONTAINER_IMAGE_TAG,
        command=command,
        pinned_packages=PINNED_PACKAGES,
        env_vars=env_vars,
        expected_inputs=list(selected_files),
        expected_outputs=["validation_report.json"],
        mc_weight_fields=MC_WEIGHT_FIELDS,
        cache_on=stream_decision.cache_on,
        cache_location=stream_decision.cache_location,
        max_cache_size_bytes=stream_decision.max_cache_size_bytes,
    )
