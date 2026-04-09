# ATLAS Open Data ScaleOps Workbench

## Overview

A local-first Python control-plane system for orchestrating access to the ATLAS 2024 research open-data release in DAOD_PHYSLITE format (65.3 TiB, 70,611 files, 9,058,437,931 events).

## Architecture

The system splits into a structured metadata/manifest layer (FastAPI + SQLite) and a documentation corpus layer, coordinated through a seed-query-manifest-subset-validate demo flow.

## Demo Flow

Run `POST /seed` to load release metadata and docs, then `POST /query` to answer questions, `POST /manifests/build` to build a file manifest, `POST /plans/subset` to select a deterministic file subset, and `POST /validate/run` to confirm remote read access via xrootd.

## Trade-offs

SQLite is used as the MVP state store for simplicity; it serializes concurrent writes and will not scale beyond a single-node local workbench.

## Limitations

The full 65.3 TiB corpus is never downloaded locally; validation reads stream small byte ranges via xrootd, which requires network access to CERN EOS infrastructure.

## Non-goals

This system is not a generic data lake, a production ATLAS analysis framework, or a replacement for ATLAS offline software (Athena/AnalysisBase).

## Citation

Data from ATLAS Open Data for Research 2024 release, record 80020, DOI 10.7483/OPENDATA.ATLAS.9HK7.P5SI. Users must follow the ATLAS citation policy at https://opendata.atlas.cern/docs/documentation/ethical_legal/citation_policy/.
