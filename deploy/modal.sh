#!/usr/bin/env bash
# Run the pinned Modal CLI with this repo's environment, authenticated from MODAL_TOKEN_ID and MODAL_TOKEN_SECRET
# in the env file (default .env; in a worktree pass ENV_FILE=<main checkout>/.env). Nothing is printed from it.
#
#   deploy/modal.sh deploy deploy/modal_app.py      deploy/modal.sh secret     (creates the app's Modal Secret)
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
MODAL=(uv run --with modal==1.6.3 modal)

read_key() {  # the value of one KEY=value line of the env file, without echoing it
  sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1 | sed -e 's/^["'\'']//' -e 's/["'\'']$//'
}

if [[ -z "${MODAL_TOKEN_ID:-}" || -z "${MODAL_TOKEN_SECRET:-}" ]]; then
  [[ -f "$ENV_FILE" ]] || { echo "no $ENV_FILE and no MODAL_TOKEN_ID/MODAL_TOKEN_SECRET in the environment" >&2; exit 1; }
  MODAL_TOKEN_ID="$(read_key MODAL_TOKEN_ID)"
  MODAL_TOKEN_SECRET="$(read_key MODAL_TOKEN_SECRET)"
  export MODAL_TOKEN_ID MODAL_TOKEN_SECRET
fi

if [[ "${1:-}" == "secret" ]]; then
  # The app's secret holds only the provider keys it calls, never the Modal token. The temporary dotenv is
  # private to this user and removed on exit.
  dotenv="$(mktemp)"
  trap 'rm -f "$dotenv"' EXIT
  chmod 600 "$dotenv"
  grep -E '^(META_API_KEY|BASETEN_API_KEY|FIREWORKS_API_KEY)=' "$ENV_FILE" > "$dotenv"
  "${MODAL[@]}" secret create spatialscout-env --from-dotenv "$dotenv" --force > /dev/null
  echo "Modal Secret spatialscout-env set ($(wc -l < "$dotenv" | tr -d ' ') keys)"
  exit 0
fi

exec "${MODAL[@]}" "$@"
