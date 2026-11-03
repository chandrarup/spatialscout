# One-command workflows. Each target is a thin wrapper; the underlying commands are listed in CLAUDE.md.
.PHONY: install types test typecheck build serve api web dev fixtures data

# The API's port; for example `make dev PORT=8010` when 8000 is taken.
PORT ?= 8000

install:  ## install Python (uv) and web (npm) dependencies from the lockfiles
	uv sync
	npm --prefix web ci

types:  ## regenerate web/src/contracts/generated.ts from the Pydantic contracts
	npm --prefix web run gen:types

test:  ## seam-1 and seam-2 tests
	uv run pytest

typecheck:  ## TypeScript typecheck of the web app against the generated contract types
	npm --prefix web run typecheck

build:  ## typecheck and build the web app into web/dist
	npm --prefix web run build

serve: build  ## build the web app, then serve it and the API on http://127.0.0.1:$(PORT)
	uv run spatialscout serve --port $(PORT)

api:  ## the API alone on :$(PORT), restarting on Python changes
	uv run spatialscout serve --reload --port $(PORT)

web:  ## the web dev server alone on :5173 with hot reload (needs `make api` for /api)
	SPATIALSCOUT_API_PORT=$(PORT) npm --prefix web run dev

dev:  ## the API (reloading) and the web dev server (hot reload, :5173) together; Ctrl-C stops both
	@trap 'kill 0' EXIT; uv run spatialscout serve --reload --port $(PORT) & SPATIALSCOUT_API_PORT=$(PORT) npm --prefix web run dev

data:  ## download any missing GSE286184 file, then validate and label all 22 sections (idempotent; raw data stays in data/)
	uv run spatialscout ingest

fixtures:  ## regenerate the synthetic section, then the stored model responses that depend on it
	uv run python scripts/build_synthetic_section.py
	uv run python scripts/build_skeleton_recording.py
