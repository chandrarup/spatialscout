"""HTTP/SSE API (FastAPI). It also serves the built web app."""

from .app import create_app

__all__ = ["create_app"]
