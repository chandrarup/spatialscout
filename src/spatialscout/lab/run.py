"""The lab: a follow-up phase on a finished investigation. Muse Wonder dispatches sub-agents from a fixed registry;
the accepted ones run concurrently with `asyncio.gather` (network and model calls interleave, figure rendering and
protein audits run in worker threads), and every start and finish is an event with its real timestamp, so overlapping
times are the record that they ran side by side. The report is assembled in code from the verdict, the claims, their
controls and the sub-agents' artifacts.

The main investigation is never touched: the lab reads its directory and writes its own `lab/` beside it."""

import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ..contracts import (
    AuditResult,
    Claim,
    ConditionName,
    DispatchProposal,
    HypothesisVerdict,
    KpmpManifest,
    LabEvent,
    LabReport,
    LabRun,
    LabTask,
    LiteratureDigest,
    LiteratureReview,
    ModelCallRecord,
    ProteinCrossCheck,
    PublicationFigure,
    VerificationResult,
)
from ..engine.protein import protein_audit
from ..gateway import ModelGateway
from . import figures as figure_renderer
from .literature import LiteratureSource, co_mention, co_mention_note, gate, records, term_groups
from .prompts import dispatch_request, literature_request

MAX_TASKS = 8
# Sub-claims with a protein-level counterpart on the KPMP images: (cell type, gene) -> (population marker, marker).
LAB_PARTICIPANTS = ("164-17", "31-10013")  # the pair the registry describes and the recorded lab ran on
PROTEIN_TWIN: dict[tuple[str, str], tuple[str, str]] = {("podocyte", "LRP2"): ("Podocalyxin", "LRP2"), ("b cell", "UMOD"): ("CD20", "UMOD")}


class Finished:
    """What the lab reads from a finished investigation's directory."""

    def __init__(self, directory: Path) -> None:
        import json

        self.directory = directory
        self.question = ""
        self.investigation_id = directory.name
        self.verdict: HypothesisVerdict | None = None
        self.claims: dict[str, Claim] = {}
        self.verifications: dict[str, VerificationResult] = {}
        for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            self.investigation_id = event.get("investigation_id", self.investigation_id)
            if event["type"] == "investigation_started":
                self.question = event.get("question", self.question)
            if event["type"] == "verdict":
                self.verdict = HypothesisVerdict.model_validate(event["verdict"])
                self.question = self.verdict.question
            if event["type"] == "claim_verified" and not event["claim"]["injected"]["is_injected"]:
                claim = Claim.model_validate(event["claim"])
                self.claims[claim.claim_id] = claim
                self.verifications[claim.claim_id] = VerificationResult.model_validate(event["verification"])
        if self.verdict is None:
            raise ValueError(f"investigation {self.investigation_id} has no verdict; the lab runs on finished investigations")

    def finding(self, finding_id: str) -> AuditResult:
        return AuditResult.model_validate_json((self.directory / "artifacts" / f"{finding_id}.json").read_text(encoding="utf-8"))

    def claim_for(self, index: int) -> Claim | None:
        v = self.verdict.verdicts[index]  # type: ignore[union-attr]
        return next((self.claims[c] for c in v.claim_ids if c in self.claims), None)


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def _pooled(result: AuditResult, condition: ConditionName):
    return next((p for p in result.pooled if p.condition == condition), None)


def _verdict_view(finished: Finished) -> list[dict[str, Any]]:
    return [
        {"index": i, "sub_claim": v.sub_claim.model_dump(mode="json"), "verdict": v.verdict, "reason": v.reason}
        for i, v in enumerate(finished.verdict.verdicts)  # type: ignore[union-attr]
    ]


def _claim_view(finished: Finished) -> list[dict[str, Any]]:
    out = []
    for claim in finished.claims.values():
        out.append({
            "finding_id": claim.finding.finding_id,
            "text": claim.text,
            "evidence_status": claim.evidence_status.value,
            "cited": {k: c.value for k, c in claim.cited.items()},
            "verification": finished.verifications[claim.claim_id].verification_status.value,
        })
    return out


def validate(proposal: DispatchProposal, finished: Finished) -> tuple[list[LabTask], list[str]]:
    """Accepted tasks, and each rejected proposal with its reason."""
    verdicts = finished.verdict.verdicts  # type: ignore[union-attr]
    tasks: list[LabTask] = []
    rejected: list[str] = []
    seen: set[tuple[str, int]] = set()
    for p in proposal.tasks:
        problem = None
        if p.sub_claim >= len(verdicts):
            problem = f"there is no sub-claim {p.sub_claim}"
        elif (p.agent, p.sub_claim) in seen:
            problem = "a duplicate of an earlier task"
        elif p.agent == "literature" and not (p.query and p.query.strip()):
            problem = "a literature task needs a query"
        elif p.agent == "protein_crosscheck":
            sub = verdicts[p.sub_claim].sub_claim
            if not any((sub.cell_type.lower(), g) in PROTEIN_TWIN for g in sub.genes):
                problem = f"no protein-level counterpart exists for {sub.cell_type} {'/'.join(sub.genes)}"
        elif p.agent == "publication_figure" and finished.claim_for(p.sub_claim) is None:
            problem = "the sub-claim rests on no verified claim"
        if problem is None and len(tasks) >= MAX_TASKS:
            problem = f"over the {MAX_TASKS}-task limit"
        if problem:
            rejected.append(f"{p.agent} for sub-claim {p.sub_claim}: {problem}")
            continue
        seen.add((p.agent, p.sub_claim))
        tasks.append(LabTask(task_id=f"lab-{len(tasks) + 1}", agent=p.agent, sub_claim=p.sub_claim, reason=p.reason, query=p.query or None))
    return tasks, rejected


def protein_check(task: LabTask, finished: Finished, artifacts_dir: Path) -> ProteinCrossCheck:
    import hashlib

    sub = finished.verdict.verdicts[task.sub_claim].sub_claim  # type: ignore[union-attr]
    population, marker = next(PROTEIN_TWIN[(sub.cell_type.lower(), g)] for g in sub.genes if (sub.cell_type.lower(), g) in PROTEIN_TWIN)
    manifest = KpmpManifest.model_validate_json((artifacts_dir / "KPMP" / "manifest.json").read_text(encoding="utf-8"))
    results = []
    for participant in [p for p in manifest.participants if p.participant_id in LAB_PARTICIPANTS]:
        folder = artifacts_dir / "KPMP" / participant.participant_id
        table_path = folder / "cells.parquet"
        table = pd.read_parquet(table_path)
        pairs = pd.read_parquet(folder / "pairs.parquet")[["a", "b"]].to_numpy()
        results.append(protein_audit(table, pairs, participant_id=participant.participant_id, role=participant.role,
                                     population_marker=population, marker=marker, thresholds=manifest.thresholds,
                                     cell_table_checksum=hashlib.sha256(table_path.read_bytes()).hexdigest(), roi=None))
    lines = []
    for r in results:
        whole = next((c for c in r.conditions if c.condition == "whole_cell"), None)
        trimmed = next((c for c in r.conditions if c.condition == "eroded_2px"), None)
        lines.append(f"{r.participant_id} ({r.role}): {_pct(whole.observed_share if whole else None)} of {r.population_cells:,} {population}+ cells "
                     f"are {marker}+, {_pct(trimmed.observed_share if trimmed else None)} with outlines trimmed 2 px, {r.label.value.replace('_', ' ')}")
    note = "; ".join(lines) + (". Descriptive: one person each, thresholds frozen on the healthy reference and not calibrated across "
                               "imaging runs, masks nucleus-sized. A second line of evidence on protein, not a replication.")
    return ProteinCrossCheck(task_id=task.task_id, sub_claim=task.sub_claim, marker=marker, population=f"{population}+ cells", results=results, note=note)


def publication_figure(task: LabTask, finished: Finished, out_dir: Path) -> PublicationFigure:
    claim = finished.claim_for(task.sub_claim)
    assert claim is not None
    result = finished.finding(claim.finding.finding_id)
    svg, pdf, png, legend, sections, cells = figure_renderer.render(result, out_dir, f"figure-{task.task_id}")
    title = f"{'/'.join(result.genes)} in {result.population.cell_type} cells under stricter molecule assignment"
    return PublicationFigure(task_id=task.task_id, sub_claim=task.sub_claim, finding_id=result.finding_id, title=title, svg=svg, pdf=pdf, png=png,
                             legend=legend, sections=sections, cells=cells)


def report(finished: Finished, literature: list[LiteratureReview], protein: list[ProteinCrossCheck], figures: list[PublicationFigure], tasks: list[LabTask]) -> LabReport:
    verdicts = finished.verdict.verdicts  # type: ignore[union-attr]
    what, why, nxt = [], [], []
    by_task = {t.task_id: t for t in tasks}
    for i, v in enumerate(verdicts):
        sub = v.sub_claim
        claim = finished.claim_for(i)
        head = f"Part {i + 1}, {sub.cell_type} {'/'.join(sub.genes)}: predicted to {'stay' if sub.predicted == 'holds' else 'fall away'} under stricter assignment; {v.verdict}."
        if claim:
            r = finished.finding(claim.finding.finding_id)
            d, n = _pooled(r, ConditionName.DEFAULT), _pooled(r, ConditionName.NUCLEUS_ONLY)
            head += (f" Pooled over {len(r.eligible_section_ids)} sections and {d.cells if d else 0:,} cells, the share went from {_pct(d.observed_value if d else None)} "
                     f"to {_pct(n.observed_value if n else None)} under nucleus-only, against {_pct(n.expectation_home_matched if n else None)} expected from random thinning.")
            verification = finished.verifications[claim.claim_id]
            why.append(f"Part {i + 1}: evidence label {claim.evidence_status.value.replace('_', ' ')} ({r.label_reason}). "
                       f"Verification {verification.verification_status.value}: " + "; ".join(f"{c.kind} {c.status}" for c in verification.checks) + ".")
            controls = [x for x in (claim.controls.random_thinning, claim.controls.label_sensitivity) if x]
            if controls:
                why.append(f"Part {i + 1}: the claim cites {len(controls)} control{'s' if len(controls) > 1 else ''} ({', '.join(controls)}).")
        else:
            why.append(f"Part {i + 1}: {v.reason}.")
        what.append(head)
        for lit in literature:
            if by_task[lit.task_id].sub_claim == i:
                why.append(f"Part {i + 1}, literature: {lit.note}")
                if lit.co_mention.records_mentioning_all == 0:
                    nxt.append(f"Part {i + 1}: none of the {lit.co_mention.records_searched} titles and abstracts read pairs {sub.genes[0]} with {sub.cell_type.lower()}s in human tissue. "
                               "A targeted search (full text, other databases) and an orthogonal assay such as RNAscope or immunostaining on human biopsies would test it directly.")
                else:
                    nxt.append(f"Part {i + 1}: read the {lit.co_mention.records_mentioning_all} records that pair {sub.genes[0]} with {sub.cell_type.lower()}s "
                               f"({', '.join(lit.co_mention.record_ids[:4])}) against this result.")
        for p in protein:
            if p.sub_claim == i:
                why.append(f"Part {i + 1}, protein: {p.note}")
                nxt.append(f"Part {i + 1}: repeat the protein check on more KPMP participants imaged with the same panel, so a healthy-versus-disease difference is not one person against one.")
        if v.verdict == "inconclusive":
            nxt.append(f"Part {i + 1}: inconclusive ({v.reason}); add sections or a second label rule before drawing a conclusion.")
    for f in figures:
        nxt.append(f"Figure for part {f.sub_claim + 1} ({f.svg}, {f.pdf}) is ready for a manuscript; its legend lists every number it shows.")
    return LabReport(what_happened=what, why=why, next_steps=nxt)


async def run_lab(
    finished: Finished,
    *,
    gateway_for: Callable[[Callable[[ModelCallRecord], None]], ModelGateway],
    literature: LiteratureSource,
    artifacts_dir: Path,
    out_dir: Path,
    clock: Callable[[], datetime],
    origin: str,
) -> LabRun:
    events: list[LabEvent] = []

    def emit(type_: str, text: str, task: LabTask | None = None, call: ModelCallRecord | None = None) -> None:
        events.append(LabEvent(seq=len(events) + 1, at_utc=clock(), type=type_, task_id=task.task_id if task else None,  # type: ignore[arg-type]
                               agent=task.agent if task else None, text=text, call=call))

    started = clock()
    emit("lab_started", "Muse Wonder reads the verdict and the verified claims, and chooses sub-agents.")
    dispatcher = gateway_for(lambda record: emit("model_call", f"{record.model} · {record.purpose}", None, record))
    request, inputs = dispatch_request(finished.question, _verdict_view(finished), _claim_view(finished))
    proposal, _ = await dispatcher.complete_json("lab_dispatch", request, inputs, DispatchProposal)
    tasks, rejected = validate(proposal, finished)
    emit("dispatched", f"{proposal.summary} {len(tasks)} sub-agent{'s' if len(tasks) != 1 else ''} start together.")
    for r in rejected:
        emit("task_rejected", r)

    reviews: list[LiteratureReview] = []
    checks: list[ProteinCrossCheck] = []
    made: list[PublicationFigure] = []

    async def literature_task(task: LabTask) -> None:
        sub = finished.verdict.verdicts[task.sub_claim].sub_claim  # type: ignore[union-attr]
        emit("subagent_started", f"Searching Europe PMC: {task.query}", task)
        data = await literature.search(task.query or "")
        hits, fetched = records(data)
        claim = finished.claim_for(task.sub_claim)
        result: dict[str, Any] = {"evidence_status": claim.evidence_status.value, "cited": {k: c.value for k, c in claim.cited.items()}} if claim else {}
        gateway = gateway_for(lambda record: emit("model_call", f"{record.model} · {record.purpose}", task, record))
        req, inp = literature_request(sub.model_dump(mode="json"), result, task.query or "", fetched)
        digest, _ = await gateway.complete_json("literature_review", req, inp, LiteratureDigest)
        kept, dropped = gate(digest, fetched)
        count = co_mention(fetched, term_groups(sub.cell_type, sub.genes))
        review = LiteratureReview(task_id=task.task_id, query=task.query or "", hit_count=hits, records=fetched, statements=kept, dropped=dropped,
                                  gap=digest.gap, co_mention=count, note=co_mention_note(count, task.query or "", hits))
        reviews.append(review)
        emit("subagent_finished", f"Read {len(fetched)} of {hits:,} hits. {len(kept)} cited statement{'s' if len(kept) != 1 else ''} kept, {len(dropped)} dropped by the citation check. {review.note}", task)

    async def protein_task(task: LabTask) -> None:
        emit("subagent_started", "Auditing the protein on both KPMP biopsies.", task)
        check = await asyncio.to_thread(protein_check, task, finished, artifacts_dir)
        checks.append(check)
        emit("subagent_finished", check.note, task)

    async def figure_task(task: LabTask) -> None:
        emit("subagent_started", "Rendering a two-panel vector figure at 180 mm.", task)
        figure = await asyncio.to_thread(publication_figure, task, finished, out_dir / "figures")
        made.append(figure)
        emit("subagent_finished", f"{figure.svg}, {figure.pdf} and {figure.png}: {figure.sections} sections, {figure.cells:,} cells.", task)

    runners = {"literature": literature_task, "protein_crosscheck": protein_task, "publication_figure": figure_task}

    async def guarded(task: LabTask) -> None:
        await asyncio.sleep(0)  # every sub-agent is scheduled before any of them runs
        try:
            await runners[task.agent](task)
        except Exception as error:  # one sub-agent failing never stops the others
            emit("subagent_failed", f"{type(error).__name__}: {error}", task)

    await asyncio.gather(*(guarded(t) for t in tasks))
    order = {t.task_id: i for i, t in enumerate(tasks)}
    reviews.sort(key=lambda r: order[r.task_id])
    checks.sort(key=lambda r: order[r.task_id])
    made.sort(key=lambda r: order[r.task_id])
    lab_report = report(finished, reviews, checks, made, tasks)
    emit("lab_finished", f"Report assembled from {len(reviews)} literature review(s), {len(checks)} protein check(s) and {len(made)} figure(s).")
    return LabRun(investigation_id=finished.investigation_id, question=finished.question, origin=origin,  # type: ignore[arg-type]
                  started_at_utc=started, finished_at_utc=clock(), dispatch_summary=proposal.summary, tasks=tasks, events=events,
                  literature=reviews, protein=checks, figures=made, report=lab_report)


__all__ = ["Finished", "run_lab", "validate", "PROTEIN_TWIN"]
