"""The evidence package: a zip of an investigation's claims, its audit log and a manifest.

The manifest records the audit log's head hash and chain check, the run mode, and the dataset's provenance.
Ticket 11 adds findings, composite figures, the replay manifest, raw-rerun instructions and the notebook.
"""

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

from ..audit import verify_chain
from ..contracts import (
    Claim,
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

CLAIMS_FILE, AUDIT_LOG_FILE, MANIFEST_FILE = "claims.json", "audit_log.jsonl", "manifest.json"


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
) -> PackageManifest:
    """Write the package zip to `path` and return its manifest."""
    contents = {
        CLAIMS_FILE: json.dumps([claim.model_dump(mode="json") for claim in claims], indent=2).encode("utf-8"),
        AUDIT_LOG_FILE: audit_log_text.encode("utf-8"),
    }
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
