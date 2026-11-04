"""Bring your own sections: audit uploaded or linked Xenium output with the built-in engine, keeping nothing."""

import asyncio
from pathlib import Path

import httpx2 as httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..lab.upload import MAX_BYTES, UploadAudit, audit_upload, gene_scales, read_table
from ..settings import Settings

router = APIRouter()
SAMPLE_FILES = ("transcripts.parquet", "cells.csv.gz")


def _sample_dir(request: Request) -> Path:
    settings: Settings = request.app.state.settings
    return settings.fixtures_dir / "upload_sample"


async def _fetch(url: str) -> bytes:
    if not url.startswith("https://"):
        raise HTTPException(status_code=400, detail={"code": "bad_url", "message": "Links must be https."})
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client, client.stream("GET", url) as response:
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail={"code": "fetch_failed", "message": f"{url} returned {response.status_code}."})
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(status_code=413, detail={"code": "too_large", "message": f"{url} is over {MAX_BYTES // 2**20} MB."})
            chunks.append(chunk)
        return b"".join(chunks)


@router.get("/upload/sample")
async def upload_sample(request: Request) -> list[dict[str, str]]:
    """The bundled sample: three crops of GSE286184 sections in Xenium's own output format."""
    root = _sample_dir(request)
    return [{"section": d.name, **{f: f"/api/upload/sample/{d.name}/{f}" for f in SAMPLE_FILES}} for d in sorted(root.iterdir()) if d.is_dir()]


@router.get("/upload/sample/{section}/{name}")
async def upload_sample_file(section: str, name: str, request: Request) -> FileResponse:
    path = _sample_dir(request) / section / name
    if name not in SAMPLE_FILES or "/" in section or not path.is_file():
        raise HTTPException(status_code=404, detail="no such sample file")
    return FileResponse(path, filename=f"{section}_{name}")


@router.post("/upload/audit")
async def upload_audit(
    request: Request,
    cell_type: str = Form(...),
    genes: str = Form(...),
    use_sample: bool = Form(False),
    transcripts: list[UploadFile] | None = File(None),
    cells: list[UploadFile] | None = File(None),
    transcripts_url: list[str] | None = Form(None),
    cells_url: list[str] | None = Form(None),
) -> UploadAudit:
    """Audit one gene set in one cell type across the uploaded sections (each a Xenium transcripts file and cells
    file, uploaded or linked by https URL; or the bundled sample). Held in memory for this request only."""
    settings: Settings = request.app.state.settings
    raw: list[tuple[str, str, bytes, str, bytes]] = []
    if use_sample:
        for d in sorted(_sample_dir(request).iterdir()):
            raw.append((d.name, "transcripts.parquet", (d / "transcripts.parquet").read_bytes(), "cells.csv.gz", (d / "cells.csv.gz").read_bytes()))
    elif transcripts and cells:
        if len(transcripts) != len(cells):
            raise HTTPException(status_code=400, detail={"code": "unpaired", "message": "Give one cells file per transcripts file."})
        for i, (t, c) in enumerate(zip(transcripts, cells, strict=True)):
            raw.append((f"section-{i + 1}", t.filename or "transcripts.parquet", await t.read(), c.filename or "cells.csv", await c.read()))
    elif transcripts_url and cells_url:
        if len(transcripts_url) != len(cells_url):
            raise HTTPException(status_code=400, detail={"code": "unpaired", "message": "Give one cells link per transcripts link."})
        for i, (t, c) in enumerate(zip(transcripts_url, cells_url, strict=True)):
            raw.append((f"section-{i + 1}", t.split("?")[0], await _fetch(t), c.split("?")[0], await _fetch(c)))
    else:
        raise HTTPException(status_code=400, detail={"code": "no_data", "message": "Upload files, give links, or use the sample."})
    wanted = [g.strip() for g in genes.split(",") if g.strip()]
    try:
        pairs = [(name, read_table(tn, tb), read_table(cn, cb)) for name, tn, tb, cn, cb in raw]
        del raw
        return await asyncio.to_thread(audit_upload, pairs, cell_type=cell_type.strip(), genes=wanted, scales=gene_scales(settings.artifacts_dir))
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail={"code": "unreadable", "message": str(error)}) from error
