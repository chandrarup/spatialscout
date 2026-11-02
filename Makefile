# One-command workflows. Each target is a thin wrapper; the underlying commands are listed in CLAUDE.md.
.PHONY: install types test typecheck build serve api web dev fixtures

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

serve: build  ## build the web app, then serve it and the API on http://127.0.0.1:8000
	uv run spatialscout serve

api:  ## the API alone on :8000, restarting on Python changes
	uv run spatialscout serve --reload

web:  ## the web dev server alone on :5173 with hot reload (needs `make api` for /api)
	npm --prefix web run dev

dev:  ## the API (reloading) and the web dev server (hot reload, :5173) together; Ctrl-C stops both
	@trap 'kill 0' EXIT; uv run spatialscout serve --reload & npm --prefix web run dev

fixtures:  ## regenerate the synthetic section, then the stored model responses that depend on it
	uv run python scripts/build_synthetic_section.py
	uv run python scripts/build_skeleton_recording.py
