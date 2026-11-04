"""The lab (follow-up phase): the dispatcher's tasks are validated against the registry, sub-agents run concurrently,
and the literature sub-agent keeps only statements that cite records Europe PMC actually returned. Model responses
are stored (hand-built here, keyed exactly as live ones); Europe PMC is a recorded response. No network."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from spatialscout.contracts import ModelResponse, RecordedCall, Recording, ReplayInfo
from spatialscout.gateway import ModelGateway, cache_key
from spatialscout.gateway.replay import ReplaySource
from spatialscout.lab.literature import RecordedLiterature
from spatialscout.lab.prompts import dispatch_request, literature_request
from spatialscout.lab.run import Finished, _claim_view, _verdict_view, run_lab
from spatialscout.lab.literature import records

ROOT = Path(__file__).resolve().parents[2]
RECORDED = ROOT / "fixtures" / "recordings" / "syn01-podocyte-lrp2" / "investigation"
QUERY = "(LRP2 OR megalin) AND podocyte AND human"
EUROPE_PMC = {
    "hitCount": 2,
    "resultList": {"result": [
        {"id": "111", "source": "MED", "pmid": "111", "title": "Megalin in rat podocytes", "pubYear": "1990",
         "abstractText": "Megalin (gp330) is expressed by rat podocytes.", "authorString": "Kerr A, B C"},
        {"id": "222", "source": "MED", "pmid": "222", "title": "Proximal tubule endocytosis in human kidney", "pubYear": "2010",
         "abstractText": "LRP2 in human proximal tubule cells.", "authorString": "Doe J"},
    ]},
}


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 4, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(milliseconds=5)
        return self.now


def stored(purpose: str, request, inputs, content: dict) -> RecordedCall:
    return RecordedCall(purpose=purpose, cache_key=cache_key(request, inputs), request=request, inputs=inputs,
                        response=ModelResponse(content=json.dumps(content), finish_reason="stop"))


def lab_for(tmp_path: Path, digest: dict):
    finished = Finished(RECORDED)
    dispatch_req, dispatch_in = dispatch_request(finished.question, _verdict_view(finished), _claim_view(finished))
    proposal = {"summary": "Check the literature, the protein and draw the figure.", "tasks": [
        {"agent": "literature", "sub_claim": 0, "reason": "Is podocyte LRP2 reported?", "query": QUERY},
        {"agent": "protein_crosscheck", "sub_claim": 0, "reason": "Protein-level counterpart.", "query": ""},
        {"agent": "publication_figure", "sub_claim": 0, "reason": "A figure for the manuscript.", "query": ""},
        {"agent": "protein_crosscheck", "sub_claim": 0, "reason": "Duplicate.", "query": ""},
        {"agent": "publication_figure", "sub_claim": 5, "reason": "No such sub-claim.", "query": ""},
    ]}
    sub = finished.verdict.verdicts[0].sub_claim
    claim = finished.claim_for(0)
    result = {"evidence_status": claim.evidence_status.value, "cited": {k: c.value for k, c in claim.cited.items()}}
    _, fetched = records(EUROPE_PMC)
    lit_req, lit_in = literature_request(sub.model_dump(mode="json"), result, QUERY, fetched)
    recording = Recording(
        info=ReplayInfo(recording_id="test-lab", recorded_at=datetime(2026, 11, 4, tzinfo=UTC), origin="hand_authored", question=finished.question, note="test"),
        calls=[stored("lab_dispatch", dispatch_req, dispatch_in, proposal), stored("literature_review", lit_req, lit_in, digest)],
    )
    source = ReplaySource(recording)
    clock = Clock()
    return asyncio.run(run_lab(
        finished,
        gateway_for=lambda on_call: ModelGateway(source, clock, run_mode="cached_tool_rerun", on_call=on_call),
        literature=RecordedLiterature({QUERY: EUROPE_PMC}), artifacts_dir=ROOT / "artifacts", out_dir=tmp_path, clock=clock, origin="replay",
    ))


def test_a_statement_citing_a_record_that_was_not_fetched_is_dropped(tmp_path):
    lab = lab_for(tmp_path, {"statements": [
        {"text": "Megalin is reported in rat podocytes.", "cites": ["PMID:111"]},
        {"text": "Human podocytes express megalin.", "cites": ["PMID:999999"]},
        {"text": "An uncited sentence.", "cites": []},
    ], "gap": "No record addresses human podocytes."})
    review = lab.literature[0]
    assert [s.cites for s in review.statements] == [["PMID:111"]]
    assert len(review.dropped) == 2 and "PMID:999999" in review.dropped[0]
    # the co-mention count is computed: record 111 is rat, record 222 is proximal tubule, so none pairs LRP2, podocyte and human
    assert review.co_mention.records_searched == 2 and review.co_mention.records_mentioning_all == 0
    assert "not a search of everything published" in review.note


def test_the_dispatcher_s_tasks_are_validated_and_the_sub_agents_overlap_in_time(tmp_path):
    lab = lab_for(tmp_path, {"statements": [], "gap": "none"})
    assert [t.agent for t in lab.tasks] == ["literature", "protein_crosscheck", "publication_figure"]
    rejected = [e.text for e in lab.events if e.type == "task_rejected"]
    assert len(rejected) == 2 and "duplicate" in rejected[0] and "no sub-claim 5" in rejected[1]
    seq = {(e.type, e.task_id): e.seq for e in lab.events if e.task_id}
    starts = [seq[("subagent_started", t.task_id)] for t in lab.tasks[1:]]
    finishes = [seq[("subagent_finished", t.task_id)] for t in lab.tasks[1:]]
    assert max(starts) < min(finishes), "the protein check and the figure were both running at once"
    figure = lab.figures[0]
    assert (tmp_path / "figures" / figure.svg).read_text().startswith("<?xml") and (tmp_path / "figures" / figure.pdf).is_file()
    assert f"{figure.sections} eligible sections" in figure.legend
    assert {r.participant_id for r in lab.protein[0].results} == {"164-17", "31-10013"}
    assert lab.report.what_happened and lab.report.next_steps
