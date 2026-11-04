"""Evidence package contracts: the export of an investigation."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from .agent import OpenQuestion
from .audit_log import ChainCheckResult
from .base import SCHEMA_VERSION, Contract, RunMode
from .dataset import DatasetManifest, FileChecksum
from .model_call import ReplayInfo


class PackageManifest(Contract):
    """manifest.json inside the evidence package: what it contains and how it was produced."""

    schema_version: str = SCHEMA_VERSION
    package_id: str
    investigation_id: str
    created_at: datetime
    run_mode: RunMode
    replay: ReplayInfo | None
    question: str
    dataset: DatasetManifest
    plan_id: str | None
    plan_hash: str | None
    files: list[FileChecksum]
    audit_log: ChainCheckResult
    review_state: Literal["work_in_progress", "reviewed"]
    claims: int
    notes: list[str]
    open_questions: list[OpenQuestion] = Field(default_factory=list, description="What the investigation could not settle within its budget.")
    reviews: int = Field(default=0, description="Review decisions recorded so far (reviews.json).")


class PackageInfo(Contract):
    """What the UI needs to offer an evidence package for download."""

    package_id: str
    download_url: str
    created_at: datetime
    files: list[str]
    audit_log: ChainCheckResult
    review_state: Literal["work_in_progress", "reviewed"]
    open_questions: list[OpenQuestion] = Field(default_factory=list)
