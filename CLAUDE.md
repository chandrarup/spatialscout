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
| `make fixtures` | Rebuilds the synthetic section, the stored model responses that depend on it, and the recorded investigation that immutable replay plays. |
| `make smoke` | `uv run spatialscout smoke`: replays the provider smoke check from `fixtures/smoke/` with no network. `--run-mode live` makes one tiny call per provider and model (cents, under the daily budget) and re-records it. |
| `make deploy` | Builds the web app and deploys (or redeploys) it with the API on Modal: `deploy/modal_app.py`. |
| `make modal-batch` | Runs `deploy/modal_batch.py` on Modal over all 22 sections with `.map()`; logs runtime and cost to `artifacts/modal_batch_gse286184.json`. |
| `make modal-secret` | Creates or replaces the Modal Secret `spatialscout-env` from the provider keys in `.env`. |

Add `PORT=8010` to `serve`, `api` or `dev` when 8000 is taken.

### Deployment

- Public URL: https://chandrarupdaka--spatialscout.us-east.modal.run (Modal app `spatialscout`). It serves `SPATIALSCOUT_DEFAULT_RUN_MODE` (`cached_tool_rerun` unless set; `immutable_replay` plays the recorded investigation). Live runs are refused unless the Modal Secret carries the live passcode and daily budget.
- The Modal targets read `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` from `.env`. In a worktree, add `ENV_FILE=<main checkout>/.env`. The app's secrets come only from the Modal Secret `spatialscout-env`; nothing from `.env` enters the image.
- One warm web container (`max_containers=1`) owns investigation state; `data/investigations/` is the Modal Volume `spatialscout-investigations`, which survives redeploys. Raw GEO files fetched by the batch job sit in the Volume `spatialscout-raw`.
- Each SSE connection ends after `SPATIALSCOUT_STREAM_WINDOW_SECONDS` (110 s by default), and the web client reconnects with `after_seq`, so streams outlast Modal's 150-second request limit.

- After changing a contract, run `make types` and commit `web/src/contracts/`.
- Stored model responses are keyed by a hash of each request plus the tool version and artifact checksum it was built from. Changing a prompt (`agent/prompts.py`), a tool, a contract inside a request, or the synthetic section makes seam-2 tests fail with `replay_miss`. Run `make fixtures` and commit `fixtures/`.
- Live runs need `SPATIALSCOUT_LIVE_PASSCODE` (sent by clients in the `X-Live-Passcode` header) and `SPATIALSCOUT_DAILY_BUDGET_USD`; spend is reserved under a `flock` in `SPATIALSCOUT_SPEND_DIR` (default `data/spend/`). Provider keys come from the environment or `SPATIALSCOUT_ENV_FILE` (default `.env`). `SPATIALSCOUT_DEFAULT_RUN_MODE` sets the mode the web app asks for.
- Each investigation persists in `data/investigations/<id>/` (`state.json`, `events.jsonl`, `audit_log.jsonl`, `artifacts/`, `package.zip`), independent of HTTP. `SPATIALSCOUT_ROOT`, `SPATIALSCOUT_INVESTIGATIONS_DIR`, `SPATIALSCOUT_FIXTURES_DIR`, `SPATIALSCOUT_RECORDINGS_DIR` and `SPATIALSCOUT_WEB_DIST` override the paths.

## Layout

- `src/spatialscout/`, one package:
  - `contracts/`: Pydantic models, the single source of truth; `schema.py` exports the JSON Schema behind the TypeScript types
  - `data/`: dataset store (the synthetic fixture now; GSE286184 in ticket 02)
  - `engine/`: deterministic science: assignment conditions, `audit_population`, `audit_section`, the region view
  - `gateway/`: model gateway: stored responses (`ReplaySource`), live calls (`LiveSource`: Meta, Baseten failing over to Fireworks, SAM 3.1, Muse Voice Transcribe), the live gate and file-locked budget, validation with one repair, per-call telemetry
  - `agent/`: orchestrator, persisted investigation, tool registry, prompts
  - `audit/`: hash-linked audit log and `verify_chain`; `export/`: evidence package; `verify/`: claim verification (ticket 10)
  - `api/`: FastAPI routes under `/api`, and the built web app at `/`; `cli.py`: `spatialscout serve`
- `tests/seam1_engine/` and `tests/seam2_api/`: the two agreed seams.
- `web/`: React, Vite, Tailwind and deck.gl; one component per panel in `src/components/`; `src/contracts/` is generated, never hand-edited.
- `fixtures/synthetic/`: section SYN-01, built by `scripts/build_synthetic_section.py`, whose docstring states the answers known by construction.
- `fixtures/recordings/<id>/recording.json`: stored model responses, built by `scripts/build_skeleton_recording.py` and marked `hand_authored`; `<id>/investigation/` is the recorded investigation immutable replay streams verbatim (`scripts/record_replay_investigation.py`).
- `fixtures/smoke/`: the provider smoke check's image, WAV and live-recorded responses.
- `artifacts/`: small committed derived outputs. `data/`: git-ignored raw data and local investigations.

## Gotchas

- Every Meta, Baseten and Fireworks model here is a reasoning model. Send a generous `max_tokens` (2,000+) and `reasoning_effort: "low"`, or content comes back empty with `finish_reason: "length"`.
- GEO `*_transcripts.parquet.gz` files are gzip-wrapped parquet. Decompress before reading.
- SAM 3.1 masks are box-local crops: global pixel = box origin + mask pixel. Concept prompts find nothing on RNA-rendered images, so use box prompts (ADR-0005).
- Muse Voice Transcribe accepts only WAV (mono 16-bit PCM, 16 or 24 kHz).
- Modal cuts web requests at 150 seconds.
- `make fixtures` cannot rebuild `fixtures/smoke/recording.json`: it holds live responses. A change to `ModelRequest` or the cache key makes it raise `StaleRecording`; re-record with `uv run spatialscout smoke --run-mode live --env-file <main checkout>/.env` (cents, needs `SPATIALSCOUT_DAILY_BUDGET_USD`).

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues on `chandrarup/spatialscout`, used through `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The default five: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
