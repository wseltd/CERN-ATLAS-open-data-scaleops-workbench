# ATLAS Open Data ScaleOps Workbench

A local-first Python **control-plane** for the ATLAS 2024 research open-data release in DAOD_PHYSLITE format.

**Scale:** 65.3 TiB · 70,611 files · 9,058,437,931 events (record 80020)
**The full corpus is never downloaded.** Remote streaming via XRootD is the default.

---

## What This Is

A data engineering system that:
- ingests official ATLAS release and collection metadata
- builds deterministic file manifests from atlasopenmagic / cernopendata-client
- plans reproducible subsets using sha256-based hash sampling (algorithm v0.1)
- decides stream-vs-cache based on configurable thresholds
- generates pinned execution plans (container image, packages, env vars)
- validates remote access against live CERN Open Data xrootd endpoints
- records provenance and citation for every run
- answers 20 structured evaluation questions about the release

This is **not** a generic chatbot, file browser, or analysis framework.

---

## Architecture

```
atlas_workbench/
  api/            FastAPI app + routers (all endpoints)
  core/           Business logic: manifest builder, subset planner,
                  stream decision, execution planner, validator,
                  query engine, provenance, seeders
  db/             SQLAlchemy models (SQLite) + session factory
  seed/           Frozen release_metadata.json fixture
fixtures/         eval_questions.json (20 questions)
scripts/          seed_runner.py, validate_runner.py
docker/           Dockerfile, docker-compose.yml
tests/unit/       34 pure unit tests (no network, no DB)
tests/integration/ API + live xrootd tests
```

**Two layers:**
1. **Structured metadata/manifest layer** — Release, Collection, Dataset, FileManifest, SubsetPlan, ExecutionPlan, ProvenanceRecord, ValidationReport in SQLite
2. **Docs corpus** — 7 official ATLAS/CERN docs fetched and stored on seed

---

## Frozen Scope (MVP)

| Record | Description | Size | Files | Events |
|--------|-------------|------|-------|--------|
| 80020 | Top-level release (DOI 10.7483/OPENDATA.ATLAS.9HK7.P5SI) | 65.3 TiB | 70,611 | 9,058,437,931 |
| 80001 | 2016 pp collision data | 35.4 TiB | 45,571 | 5,383,448,881 |
| 80000 | 2015 pp collision data | 9.3 TiB | 10,049 | 1,694,555,330 |
| 80017 | Top nominal MC (DSID 410470 = ttbar) | 855.3 GiB | 437 | 63,507,400 |

Release tag: `2024r-pp`

---

## Quick Start

```bash
# Install
pip install -e ".[test]"

# Seed metadata (no docs fetch):
python scripts/seed_runner.py --skip-docs

# Start API:
uvicorn atlas_workbench.api.main:app --reload

# Seed via API (includes docs):
curl -X POST http://localhost:8000/seed -H 'Content-Type: application/json' -d '{}'

# Query:
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is the total size and file count of the ATLAS 2024 release?"}'

# Build manifest (uses atlasopenmagic live):
curl -X POST http://localhost:8000/manifests/build \
  -H 'Content-Type: application/json' \
  -d '{"collection_id": "dsid:410470", "protocol": "root"}'

# Build subset plan:
curl -X POST http://localhost:8000/plans/subset \
  -H 'Content-Type: application/json' \
  -d '{"manifest_id": "<manifest_id_from_above>"}'

# Validate (requires xrootd to eospublic.cern.ch:1094):
python scripts/validate_runner.py --dataset-ref dsid:410470 --protocol root
```

---

## Demo Flow

```
POST /seed          → loads 1 release, 3 collections, 1 dataset, 7 doc pages
POST /query         → answers questions about scale, access, citation
POST /manifests/build → builds file manifest (calls atlasopenmagic live)
POST /plans/subset  → selects N files deterministically (sha256 hash sort)
POST /plans/execution → emits pinned container + package execution plan
POST /validate/run  → streams from CERN xrootd, reads CollectionTree
POST /eval/run      → runs all 20 evaluation questions, persists results
GET  /eval/results/{run_id} → retrieve results
GET  /evidence/latest       → audit trail of validation runs
```

---

## Deterministic Subset Algorithm (v0.1)

1. Normalize URLs (strip `simplecache::` prefix)
2. `sha256(url.encode('utf-8'))` per file
3. Sort by `(sha256_hex, url)`
4. Select first N: **N=3** for collision, **N=1** for MC
5. Record `plan_hash = sha256(ordered_selected_urls)`, `algorithm_version`, `N`, `hashing_method`

---

## Stream vs Cache Decision

- **Default:** `root://` XRootD streaming
- **Cache if:** total subset size < 10 GiB → fsspec simplecache to `/tmp/atlas_cache`
- **Fallback URL rewrite:** `root://eospublic.cern.ch//eos/opendata/...` → `http://opendata.cern.ch/eos/opendata/...`

---

## Execution Plan Pins

```
Container: gitlab-registry.cern.ch/atlas/athena/analysisbase:25.2.2
uproot==5.1.2  awkward==2.5.0  vector==1.1.1
atlasopenmagic==1.9.0  cernopendata-client==1.0.2
```

---

## MC Event Weight

`weight = cross_section × filter_efficiency × k_factor`

Never use raw `cross_section` alone. For DSID 410470: `831.76 × 0.5433 × 1.0`.

---

## Trade-Offs

- **SQLite** serialises writes and does not support concurrent users; acceptable for a single-node local workbench. Migrate to PostgreSQL for multi-user deployments.
- **Deterministic subsets** with N=3 (collision) and N=1 (MC) are deliberately small to avoid large xrootd transfers during validation. Increase N when network and storage allow.
- **No vector search** — the query engine is deterministic keyword dispatch, not semantic similarity. This makes answers fully reproducible and auditable at the cost of query flexibility.
- **atlasopenmagic==1.9.0** is pinned; the upstream API may change between releases. Pin-and-test is the correct update strategy.

## Non-Goals

- This is **not** a production ATLAS analysis framework or a replacement for Athena/AnalysisBase.
- This is **not** a generic data lake, object store, or scientific data repository.
- This is **not** designed to download or process the full 65.3 TiB release locally.
- This is **not** a generative-AI chatbot; all answers are evidence-backed deterministic lookups.
- Multi-experiment support (beyond ATLAS) is explicitly out of scope for v0.1.

## Limitations

- XRootD streaming requires network access to `eospublic.cern.ch:1094`
- The full 65.3 TiB release is never downloaded; only small byte ranges are streamed for validation
- SQLite serialises writes; use PostgreSQL for multi-user deployments
- `atlasopenmagic==1.9.0` and `cernopendata-client==1.0.2` API surfaces are pinned

---

## Citation

ATLAS Collaboration (2024). ATLAS Open Data for Research (DAOD_PHYSLITE, Run 2).
CERN Open Data Portal. DOI: 10.7483/OPENDATA.ATLAS.9HK7.P5SI

Data are released under **CC0 1.0**. ATLAS requests citation of the dataset DOI(s) used.
Citation policy: https://opendata.atlas.cern/docs/documentation/ethical_legal/citation_policy/
