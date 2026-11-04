"""Contracts for the lab: the follow-up phase that runs on a finished investigation's verified claims. A dispatcher
(Muse Wonder) chooses sub-agents from a fixed registry; the chosen sub-agents run concurrently, and each writes a
computed or fetched artifact. Nothing here is a verdict: the lab adds context to one."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract
from .model_call import ModelCallRecord
from .protein import ProteinAuditResult

LabAgent = Literal["literature", "protein_crosscheck", "publication_figure"]


class LabTaskProposal(Contract):
    """One sub-agent the dispatcher asks for, about one sub-claim of the verdict."""

    agent: LabAgent
    sub_claim: int = Field(ge=0, description="Index of the sub-claim in the verdict, from 0.")
    reason: str = Field(description="One sentence: why this sub-agent, for this sub-claim.")
    query: str | None = Field(
        default=None,
        description="Literature only: a Europe PMC query (boolean syntax, for example '(LRP2 OR megalin) AND podocyte AND human').",
    )


class DispatchProposal(Contract):
    """The dispatcher's answer: the sub-agents to start, at most eight."""

    summary: str = Field(description="One sentence on what the lab will do and why.")
    tasks: list[LabTaskProposal]


class LabTask(Contract):
    task_id: str
    agent: LabAgent
    sub_claim: int
    reason: str
    query: str | None = None


class LiteratureRecord(Contract):
    """One record exactly as Europe PMC returned it (abstract cut to 1,500 characters)."""

    record_id: str = Field(description="'PMID:<n>' when the record has a PubMed id, else '<source>:<id>'.")
    pmid: str | None = None
    doi: str | None = None
    title: str
    journal: str | None = None
    year: int | None = None
    first_author: str | None = None
    abstract: str = ""
    url: str


class LiteratureStatementDraft(Contract):
    text: str = Field(description="One sentence about what the cited records report. No claim beyond them.")
    cites: list[str] = Field(description="record_id values of the records the sentence rests on; at least one.")


class LiteratureDigest(Contract):
    """Muse Spark's reading of the fetched records about one sub-claim."""

    statements: list[LiteratureStatementDraft]
    gap: str = Field(description="One sentence: what these records do not address about the sub-claim.")


class LiteratureStatement(Contract):
    text: str
    cites: list[str]


class CoMention(Contract):
    """A deterministic count over the fetched records: how many mention every term group in title or abstract."""

    term_groups: list[list[str]]
    records_searched: int
    records_mentioning_all: int
    record_ids: list[str]


class LiteratureReview(Contract):
    task_id: str
    query: str
    hit_count: int = Field(description="Europe PMC's total hits for the query; only `records` were read.")
    records: list[LiteratureRecord]
    statements: list[LiteratureStatement] = Field(description="Statements that passed the citation check.")
    dropped: list[str] = Field(default_factory=list, description="Statements removed, with the reason.")
    gap: str = ""
    co_mention: CoMention
    note: str = Field(description="What the co-mention count supports, worded as a count, never as novelty.")


class ProteinCrossCheck(Contract):
    task_id: str
    sub_claim: int
    marker: str
    population: str
    results: list[ProteinAuditResult]
    note: str


class PublicationFigure(Contract):
    task_id: str
    sub_claim: int
    finding_id: str
    title: str
    svg: str
    pdf: str
    png: str
    legend: str
    sections: int
    cells: int


class LabEvent(Contract):
    seq: int
    at_utc: datetime
    type: Literal["lab_started", "dispatched", "task_rejected", "subagent_started", "model_call", "subagent_finished", "subagent_failed", "lab_finished"]
    task_id: str | None = None
    agent: LabAgent | None = None
    text: str
    call: ModelCallRecord | None = None


class LabReport(Contract):
    """The written analysis, assembled deterministically from the verdict, the claims, their controls and the lab's
    artifacts. Next steps are suggestions, each tied to the artifact it comes from."""

    what_happened: list[str]
    why: list[str]
    next_steps: list[str]


class LabRun(Contract):
    schema_version: str = SCHEMA_VERSION
    investigation_id: str
    question: str
    origin: Literal["live", "replay", "hand_authored"]
    started_at_utc: datetime
    finished_at_utc: datetime
    dispatch_summary: str
    tasks: list[LabTask]
    events: list[LabEvent]
    literature: list[LiteratureReview] = Field(default_factory=list)
    protein: list[ProteinCrossCheck] = Field(default_factory=list)
    figures: list[PublicationFigure] = Field(default_factory=list)
    report: LabReport
