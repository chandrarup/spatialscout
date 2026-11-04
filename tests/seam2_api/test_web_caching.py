"""The built web app's caching: a browser must never keep a stale index.html after a redeploy.

A judge who opened the public URL before a redeploy kept the old index.html, and with it an old bundle, because the
page was cacheable. The page itself must be revalidated every time; the content-hashed assets may be cached for long.
"""

import os
from dataclasses import replace

from fastapi.testclient import TestClient

from spatialscout.api import create_app

from .conftest import make_settings


def built_web_app(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<script src="/assets/index-abc123.js"></script>')
    (dist / "assets" / "index-abc123.js").write_text("console.log('hashed bundle')")
    return replace(make_settings(tmp_path), web_dist=dist)


def test_the_page_is_revalidated_on_every_visit(tmp_path):
    with TestClient(create_app(built_web_app(tmp_path))) as client:
        for path in ("/", "/index.html"):
            response = client.get(path)
            assert response.status_code == 200
            assert "no-cache" in response.headers["cache-control"]


def test_a_redeployed_page_of_the_same_size_is_never_answered_not_modified(tmp_path):
    """Modal mounts every file with mtime 0, so a new index.html of the same size gets the old ETag; a browser
    revalidating with it must still receive the new page."""
    settings = built_web_app(tmp_path)
    page = settings.web_dist / "index.html"
    os.utime(page, (0, 0))
    with TestClient(create_app(settings)) as client:
        first = client.get("/")
        validators = {k: v for k, v in (("if-none-match", first.headers.get("etag")), ("if-modified-since", first.headers.get("last-modified"))) if v}
        page.write_text('<script src="/assets/index-def456.js"></script>')
        os.utime(page, (0, 0))
        again = client.get("/", headers=validators)
        assert again.status_code == 200
        assert "index-def456" in again.text


def test_content_hashed_assets_may_be_cached_for_long(tmp_path):
    with TestClient(create_app(built_web_app(tmp_path))) as client:
        response = client.get("/assets/index-abc123.js")
        assert response.status_code == 200
        assert "immutable" in response.headers["cache-control"]
