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

## Gotchas

- Every Meta, Baseten and Fireworks model here is a reasoning model. Send a generous `max_tokens` (2,000+) and `reasoning_effort: "low"`, or content comes back empty with `finish_reason: "length"`.
- GEO `*_transcripts.parquet.gz` files are gzip-wrapped parquet. Decompress before reading.
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
