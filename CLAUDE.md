# SpatialScout

Hackathon build for the Meta Global AI Developer Hackathon (submissions due 2026-11-04, 9:00 PM ET). An agent on Meta's models checks which kidney spatial-transcriptomics findings survive changes to how RNA molecules are assigned to cells.

## Before you change anything

- **Vocabulary**: use the terms in `GLOSSARY.md` in code, tests, issues and UI copy.
- **Decisions**: read the `docs/adr/` entries for the area you touch, and surface any conflict instead of overriding it.
- **Facts** about the data, Meta models and partner platforms: `docs/research/`. They were checked live on Nov 2 and beat memory.
- **Scope**: spec issue #1 and its sub-issues (`gh issue view <n>`; index in `docs/spec/tickets.md`). `docs/spec/` also holds the review trail.

## Guardrails

- Every number the product shows or writes comes from a computed artifact, so the demo holds up under questioning (ADR-0001).
- Secrets stay in `.env` on the backend and raw data stays in `data/`; both are git-ignored. Run `python3 -I scripts/check_secrets.py` after staging and before every commit.
- Tests live at the two agreed seams: the analysis engine's public operations, on hand-built molecule tables with known answers; and the HTTP/SSE API, through FastAPI's test client with recorded model responses.
- In a git worktree, `.env` and `data/raw/` exist only in the main checkout at `/Users/chandrarupdaka/Documents/Personal/Projects/Meta-Hackathon`. Read them from there.

## Commands

Run from the repo root, after `make install` (uv and npm, from the lockfiles).

| Command | Does |
| --- | --- |
| `make serve` | Builds the web app, then serves it and the API at http://127.0.0.1:8000 (`uv run spatialscout serve`). |
| `make dev` | API with Python reload, plus the Vite dev server with hot reload at http://localhost:5173 (proxies `/api`). |
| `make test` | `uv run pytest`: `tests/seam1_engine` and `tests/seam2_api`, with outbound network blocked. |
| `make typecheck` | `npm --prefix web run typecheck`, against the generated contract types. |
| `make types` | `npm --prefix web run gen:types`: regenerates `web/src/contracts/` from the Pydantic contracts. |
| `make build` | Typechecks and builds the web app into `web/dist`. |
| `make fixtures` | Rebuilds the synthetic section, then the stored model responses that depend on it. |
| `make data` | `uv run spatialscout ingest`: downloads any missing GSE286184 file, validates and labels all 22 sections, and rewrites `artifacts/GSE286184/`. Idempotent. |

Add `PORT=8010` to `serve`, `api` or `dev` when 8000 is taken.

- After changing a contract, run `make types` and commit `web/src/contracts/`.
- Stored model responses are keyed by a hash of each request plus the tool version and artifact checksum it was built from. Changing a prompt (`agent/prompts.py`), a tool, a contract inside a request, or the synthetic section makes seam-2 tests fail with `replay_miss`. Run `make fixtures` and commit `fixtures/`.
- Each investigation persists in `data/investigations/<id>/` (`state.json`, `events.jsonl`, `audit_log.jsonl`, `artifacts/`, `package.zip`), independent of HTTP. `SPATIALSCOUT_ROOT`, `SPATIALSCOUT_INVESTIGATIONS_DIR`, `SPATIALSCOUT_FIXTURES_DIR`, `SPATIALSCOUT_RECORDINGS_DIR` and `SPATIALSCOUT_WEB_DIST` override the paths.
- GSE286184 paths: `SPATIALSCOUT_RAW_DIR` (raw GEO files, default `data/raw/GSE286184`), `SPATIALSCOUT_PROCESSED_DIR` (validated tables, default `data/processed/GSE286184`) and `SPATIALSCOUT_ARTIFACTS_DIR` (default `artifacts`). In a worktree, set `SPATIALSCOUT_RAW_DIR` to the main checkout's `data/raw/GSE286184` before `make data`.

## Layout

- `src/spatialscout/`, one package:
  - `contracts/`: Pydantic models, the single source of truth; `schema.py` exports the JSON Schema behind the TypeScript types
  - `data/`: dataset store: the synthetic fixture and GSE286184 (`gse286184.py` ingest, `validation.py`, the frozen `label_rules.py`)
  - `engine/`: deterministic science: assignment conditions, `audit_population`, `audit_section`, the region view
  - `gateway/`: model gateway; stored responses only (`ReplaySource`) until ticket 03 adds live and immutable-replay sources
  - `agent/`: orchestrator, persisted investigation, tool registry, prompts
  - `audit/`: hash-linked audit log and `verify_chain`; `export/`: evidence package; `verify/`: claim verification (ticket 10)
  - `api/`: FastAPI routes under `/api`, and the built web app at `/`; `cli.py`: `spatialscout serve`
- `tests/seam1_engine/` and `tests/seam2_api/`: the two agreed seams.
- `web/`: React, Vite, Tailwind and deck.gl; one component per panel in `src/components/`; `src/contracts/` is generated, never hand-edited.
- `fixtures/synthetic/`: section SYN-01, built by `scripts/build_synthetic_section.py`, whose docstring states the answers known by construction.
- `fixtures/recordings/<id>/recording.json`: stored model responses, built by `scripts/build_skeleton_recording.py` and marked `hand_authored`.
- `artifacts/`: small committed derived outputs; `artifacts/GSE286184/` holds the manifest, capability report and label rules with per-section counts. `data/`: git-ignored raw data and local investigations.

## Gotchas

- Every Meta, Baseten and Fireworks model here is a reasoning model. Send a generous `max_tokens` (2,000+) and `reasoning_effort: "low"`, or content comes back empty with `finish_reason: "length"`.
- GEO `*_transcripts.parquet.gz` files are gzip-wrapped parquet. Decompress before reading.
- GSM8720419 (x11) holds the same content as GSM8720418 (x10): 21 distinct sections. The manifest marks it `duplicate_of`; count the pair once.
- SAM 3.1 masks are box-local crops: global pixel = box origin + mask pixel. Concept prompts find nothing on RNA-rendered images, so use box prompts (ADR-0005).
- Muse Voice Transcribe accepts only WAV (mono 16-bit PCM, 16 or 24 kHz).
- Modal cuts web requests at 150 seconds.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues on `chandrarup/spatialscout`, used through `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The default five: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
