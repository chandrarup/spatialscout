"""SpatialScout on Modal (ADR-0004): one public web container serving the API and the built web app.

Deploy or redeploy (builds the web app first):  make deploy
The per-section batch job is a separate app: deploy/modal_batch.py (make modal-batch).

`web` is pinned to exactly one warm container because one process owns each investigation's in-memory event
stream; `data/investigations/` lives on a Modal Volume so investigations survive restarts and redeploys. Secrets
come only from the Modal Secret `spatialscout-env` (`make modal-secret`); nothing from `.env` enters the image.
"""

from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[1]
APP_NAME = "spatialscout"

app = modal.App(APP_NAME)
investigations_volume = modal.Volume.from_name("spatialscout-investigations", create_if_missing=True)
secrets = [modal.Secret.from_name("spatialscout-env")]

INVESTIGATIONS_MOUNT = "/state"
web_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_sync(str(REPO), frozen=True, extra_options="--no-dev")  # third-party deps, exactly as uv.lock pins them
    .env(
        {
            # configs/ (the frozen marker pairs) and artifacts/ (manifest, label rules, audit results) sit under it.
            "SPATIALSCOUT_ROOT": "/root",
            "SPATIALSCOUT_FIXTURES_DIR": "/root/fixtures",
            "SPATIALSCOUT_RECORDINGS_DIR": "/root/fixtures/recordings",
            "SPATIALSCOUT_WEB_DIST": "/root/web-dist",
            "SPATIALSCOUT_INVESTIGATIONS_DIR": f"{INVESTIGATIONS_MOUNT}/investigations",
            # Modal cuts web requests at 150 s; each SSE connection ends well before that and the client reconnects.
            "SPATIALSCOUT_STREAM_WINDOW_SECONDS": "110",
        }
    )
    # Only the package, fixtures, configs, committed artifacts and the built web app are shipped: never the repo
    # root, so `.env` cannot be.
    .add_local_python_source("spatialscout")
    .add_local_dir(REPO / "fixtures", "/root/fixtures")
    .add_local_dir(REPO / "configs", "/root/configs")
    .add_local_dir(REPO / "artifacts", "/root/artifacts")
    .add_local_dir(REPO / "web" / "dist", "/root/web-dist")
)


@app.function(
    image=web_image,
    secrets=secrets,
    volumes={INVESTIGATIONS_MOUNT: investigations_volume},
    min_containers=1,  # kept warm: no cold start for a judge
    max_containers=1,  # one process owns investigation state and the in-memory event streams
    cpu=1.0,
    memory=1024,
    timeout=600,
)
@modal.concurrent(max_inputs=100)  # an open SSE stream must not block `POST /approve` on the single container
@modal.asgi_app(label=APP_NAME)
def web():
    from spatialscout.api import create_app

    return create_app()
