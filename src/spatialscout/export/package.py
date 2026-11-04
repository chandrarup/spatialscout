"""The evidence package: a zip of an investigation's claims, findings and controls, composite figures, review
decisions, audit log, replay manifest, rerun instructions, the verification notebook and a manifest.

The manifest records every other file's checksum, the audit log's head hash and chain check, the run mode, the review
state and the dataset's provenance.
"""

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

from ..audit import verify_chain
from ..contracts import (
    Claim,
    ModelCallRecord,
    ReviewDecision,
    DatasetManifest,
    FileChecksum,
    OpenQuestion,
    PackageManifest,
    Plan,
    ReplayInfo,
    ReviewStatus,
    RunMode,
    new_id,
)

from .notebook import notebook, script

CLAIMS_FILE, AUDIT_LOG_FILE, MANIFEST_FILE = "claims.json", "audit_log.jsonl", "manifest.json"
REVIEWS_FILE, REPLAY_FILE, RERUN_FILE = "reviews.json", "replay.json", "RERUN.md"
NOTEBOOK_FILE, SCRIPT_FILE = "verify.ipynb", "verify_package.py"

RERUN = """# Rerunning this investigation

## Check the package (no raw data needed)

Run `verify.ipynb` top to bottom, or `python3 verify_package.py`, in this folder. It checks the file checksums, the
audit log's hash chain against the manifest's head hash, every cited number against `artifacts/`, and each audit
result's arithmetic from its own counts.

## Replay the model responses

`replay.json` lists every model call with its cache key. With the SpatialScout repository at the commit that made this
package, `make install && make serve`, then ask the question in `manifest.json` in the run mode it records; a cached
tool rerun re-runs every tool and serves the stored responses for the same keys.

## Rerun from raw data

1. `make install`
2. `make data`: downloads GSE286184 from GEO (GSE286184) and validates and labels every section.
3. `make audit`: recomputes the audit results, controls and composite figures into `artifacts/GSE286184/audit/`.
4. `make benchmark`: recomputes the verifier's numerical checks from the molecule tables.

Synthetic data (SYN-01) is rebuilt by `make fixtures`; its answers are known by construction.
"""


def build_package(
    path: Path,
    *,
    investigation_id: str,
    question: str,
    run_mode: RunMode,
    replay: ReplayInfo | None,
    dataset: DatasetManifest,
    plan: Plan | None,
    claims: list[Claim],
    audit_log_text: str,
    created_at: datetime,
    open_questions: list[OpenQuestion] | None = None,
    directory: Path | None = None,
    reviews: list[ReviewDecision] | None = None,
    model_calls: list[ModelCallRecord] | None = None,
) -> PackageManifest:
    """Write the package zip to `path` and return its manifest. `directory` is the investigation's folder, whose
    `artifacts/` and `figures/` are exported."""
    reviews = reviews or []
    contents = {
        CLAIMS_FILE: json.dumps([claim.model_dump(mode="json") for claim in claims], indent=2).encode("utf-8"),
        AUDIT_LOG_FILE: audit_log_text.encode("utf-8"),
        REVIEWS_FILE: json.dumps([r.model_dump(mode="json") for r in reviews], indent=2).encode("utf-8"),
        REPLAY_FILE: json.dumps({
            "run_mode": run_mode,
            "recording": replay.model_dump(mode="json") if replay else None,
            "model_calls": [call.model_dump(mode="json") for call in model_calls or []],
        }, indent=2).encode("utf-8"),
        RERUN_FILE: RERUN.encode("utf-8"),
        NOTEBOOK_FILE: notebook().encode("utf-8"),
        SCRIPT_FILE: script().encode("utf-8"),
    }
    if directory is not None:
        for folder in ("artifacts", "figures"):
            for file in sorted((directory / folder).glob("*")) if (directory / folder).is_dir() else []:
                if file.suffix in (".json", ".png"):
                    contents[f"{folder}/{file.name}"] = file.read_bytes()
    unreviewed = any(claim.review_status == ReviewStatus.UNREVIEWED for claim in claims)
    manifest = PackageManifest(
        package_id=new_id("pkg"),
        investigation_id=investigation_id,
        created_at=created_at,
        run_mode=run_mode,
        replay=replay,
        question=question,
        dataset=dataset,
        plan_id=plan.plan_id if plan else None,
        plan_hash=plan.plan_hash if plan else None,
        files=[FileChecksum(path=name, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)) for name, data in contents.items()],
        audit_log=verify_chain(audit_log_text),
        review_state="work_in_progress" if unreviewed or not claims else "reviewed",
        claims=len(claims),
        notes=_notes(replay, claims, dataset),
        open_questions=open_questions or [],
        reviews=len(reviews),
    )
    contents[MANIFEST_FILE] = manifest.model_dump_json(indent=2).encode("utf-8")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), data)
    return manifest


def _notes(replay: ReplayInfo | None, claims: list[Claim], dataset: DatasetManifest) -> list[str]:
    notes = []
    if any(claim.review_status == ReviewStatus.UNREVIEWED for claim in claims):
        notes.append("Work in progress: at least one claim has no review decision.")
    if any(claim.verification_status == "pending" for claim in claims):
        notes.append("Verification has not run on at least one claim (pending).")
    if replay is not None and replay.origin == "hand_authored":
        notes.append(f"Model responses come from recording {replay.recording_id}, hand-authored without calling a model.")
    if dataset.synthetic:
        notes.append(f"Dataset {dataset.dataset_id} is synthetic: its answers are known by construction, not measured in tissue.")
    return notes
