"""Seam 2: the agent loop through the HTTP/SSE API, as cached tool reruns on hand-authored recordings.

The scenarios live in fixtures/agent_scenarios/ (built by scripts/build_skeleton_recording.py), one recording per
question: the hero question with the agent's follow-up controls, an unsupported plan, a re-plan, budget exhaustion
and invalid follow-ups. The walking skeleton's recording is the run in which the agent skips its controls.
"""

import dataclasses
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from spatialscout.api import create_app

from .conftest import RECORDED_QUESTION, REPO, make_settings
from .fake_providers import FakeProviders
from .test_investigation_api import approve, read_events
from .test_live_runs import live_app, run_live

HERO = "Do the podocytes in the synthetic section really carry LRP2 and CUBN, or is that segmentation?"
UNSUPPORTED = "Re-segment the synthetic section with Proseg and recount podocyte LRP2."
REPLAN = "Would re-segmenting the synthetic section change podocyte LRP2?"
BUDGET = "Which synthetic cell populations keep their marker molecules under nucleus-only assignment?"
INVALID = "Is podocyte LRP2 in the synthetic section an assignment effect?"


@pytest.fixture
def scenarios(tmp_path):
    settings = dataclasses.replace(make_settings(tmp_path), recordings_dir=REPO / "fixtures" / "agent_scenarios")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def ask(client, question):
    response = client.post("/api/investigations", json={"question": question})
    assert response.status_code == 201, response.text
    investigation_id = response.json()["investigation_id"]
    read_events(client, investigation_id, until={"plan_proposed", "error"})
    return investigation_id


def run(client, question):
    investigation_id = ask(client, question)
    approve(client, investigation_id)
    return investigation_id, read_events(client, investigation_id)


def of_type(events, kind):
    return [event for event in events if event["type"] == kind]


def test_in_the_hero_run_the_agent_requests_both_controls_citing_the_audit_and_the_claim_cites_them(scenarios):
    investigation_id, events = run(scenarios, HERO)

    started = of_type(events, "tool_started")
    assert [(e["tool"], e["observation_id"], e["cites_observation_id"]) for e in started] == [
        ("audit_population", "obs-1", None),
        ("run_random_thinning_control", "obs-2", "obs-1"),
        ("run_label_sensitivity_check", "obs-3", "obs-1"),
    ]
    first_decision = of_type(events, "agent_decision")[0]
    assert first_decision["observation_id"] == "obs-1"
    assert [(r["tool"], r["cites_observation_id"], r["status"]) for r in first_decision["requests"]] == [
        ("run_random_thinning_control", "obs-1", "accepted"),
        ("run_label_sensitivity_check", "obs-1", "accepted"),
    ]
    assert all(r["reason"] for r in first_decision["requests"])
    # the agent reads every observation, its controls included
    assert [d["observation_id"] for d in of_type(events, "agent_decision")] == ["obs-1", "obs-2", "obs-3"]
    finished = {e["tool"]: e["artifact_id"] for e in of_type(events, "tool_finished")}
    [claim] = [e["claim"] for e in of_type(events, "claim_drafted")]
    assert claim["controls"] == {
        "random_thinning": finished["run_random_thinning_control"],
        "label_sensitivity": finished["run_label_sensitivity_check"],
    }
    assert claim["controls"]["random_thinning"].startswith("ctl-")
    # the claim cites the control's own number: 4 podocytes under the alternative rule (3 by construction plus PT cell C06)
    cited = {n["source"]: n["value"] for n in claim["cited"].values()}
    assert cited[f"controls[{finished['run_label_sensitivity_check']}].arms[synthetic-alternative].cells_labelled"] == 4
    assert scenarios.get(f"/api/investigations/{investigation_id}").json()["status"] == "complete"


LIVE_HERO = "Do the podocytes this atlas calls 'endocytic' really carry LRP2 and CUBN, or is that segmentation?"


def test_the_recorded_live_hero_run_replays_with_every_control_requested_by_the_agent_citing_an_earlier_observation(client):
    """The live GSE286184 hero run, as immutable replay. Checks its structure, never its outcome (ADR-0001)."""
    response = client.post("/api/investigations", json={"question": LIVE_HERO, "run_mode": "immutable_replay"})
    assert response.status_code == 201, response.text
    snapshot = response.json()
    events = snapshot["events"]

    assert (snapshot["run_mode"], snapshot["replay"]["origin"], snapshot["status"]) == ("immutable_replay", "live", "complete")
    accepted = {r["request_id"]: r for d in of_type(events, "agent_decision") for r in d["requests"] if r["status"] == "accepted"}
    seen: list[str] = []
    for event in of_type(events, "tool_started"):
        if event["tool"] != "audit_population" or event["request_id"]:
            assert event["request_id"] in accepted, "a tool ran that the agent never requested"
            assert event["cites_observation_id"] in seen
            assert accepted[event["request_id"]]["cites_observation_id"] == event["cites_observation_id"]
        seen.append(event["observation_id"])
    ran = {e["artifact_id"] for e in of_type(events, "tool_finished")}
    for claim in snapshot["claims"]:
        for control_id in claim["controls"].values():
            assert control_id is None or control_id in ran


def test_the_audit_log_records_each_follow_up_with_the_observation_it_cites(scenarios):
    investigation_id, _ = run(scenarios, HERO)
    package = zipfile.ZipFile(io.BytesIO(scenarios.get(f"/api/investigations/{investigation_id}/package").content))
    audit = [json.loads(line) for line in package.read("audit_log.jsonl").decode().splitlines()]

    calls = [(e["payload"]["tool"], e["payload"]["observation_id"], e["payload"]["request_id"], e["payload"]["cites_observation_id"])
             for e in audit if e["kind"] == "tool_call"]
    assert calls == [
        ("audit_population", "obs-1", None, None),
        ("run_random_thinning_control", "obs-2", "req-1", "obs-1"),
        ("run_label_sensitivity_check", "obs-3", "req-2", "obs-1"),
    ]
    assert [e["payload"]["observation_id"] for e in audit if e["kind"] == "agent_decision"] == ["obs-1", "obs-2", "obs-3"]


def test_when_the_agent_skips_its_controls_none_is_run_on_its_behalf(client):
    _, events = run(client, RECORDED_QUESTION)

    assert [e["tool"] for e in of_type(events, "tool_started")] == ["audit_population"]
    [decision] = of_type(events, "agent_decision")
    assert decision["requests"] == []
    [claim] = [e["claim"] for e in of_type(events, "claim_drafted")]
    assert claim["controls"] == {"random_thinning": None, "label_sensitivity": None}


def test_nothing_runs_before_approval_and_the_approved_plan_hash_is_frozen_in_state_and_audit_log(scenarios, tmp_path):
    investigation_id = ask(scenarios, HERO)
    before = scenarios.get(f"/api/investigations/{investigation_id}").json()
    assert before["status"] == "awaiting_approval"
    assert [e["type"] for e in before["events"]] == ["model_call", "plan_proposed"]
    assert before["approved_plan_hash"] is None

    approve(scenarios, investigation_id)
    read_events(scenarios, investigation_id)

    state = json.loads((tmp_path / "investigations" / investigation_id / "state.json").read_text())
    audit = [json.loads(line) for line in (tmp_path / "investigations" / investigation_id / "audit_log.jsonl").read_text().splitlines()]
    [approved] = [e["payload"] for e in audit if e["kind"] == "plan_approved"]
    assert state["approved_plan_hash"] == approved["plan_hash"]
    assert len(state["approved_plan_hash"]) == 64
    kinds = [e["kind"] for e in audit]
    assert kinds.index("plan_approved") < kinds.index("tool_call")


def test_a_plan_naming_an_unsupported_tool_is_rejected_and_replanned_once_then_the_limitation_is_reported(scenarios):
    investigation_id = ask(scenarios, UNSUPPORTED)
    snapshot = scenarios.get(f"/api/investigations/{investigation_id}").json()

    rejected = of_type(snapshot["events"], "plan_rejected")
    assert [(e["by"], e["attempt"], e["tools"]) for e in rejected] == [
        ("validator", 1, ["resegment_with_proseg"]), ("validator", 2, ["resegment_with_proseg"]),
    ]
    assert "not a tool in the registry" in rejected[0]["reason"]
    assert [e["call"]["purpose"] for e in of_type(snapshot["events"], "model_call")] == ["plan", "replan"]
    assert snapshot["status"] == "failed" and snapshot["plan"] is None
    error = snapshot["events"][-1]
    assert error["code"] == "plan_unsupported"
    assert "audit_population" in error["message"]
    assert of_type(snapshot["events"], "tool_started") == []


def test_a_rejected_plan_whose_replan_is_supported_awaits_approval(scenarios):
    investigation_id = ask(scenarios, REPLAN)
    snapshot = scenarios.get(f"/api/investigations/{investigation_id}").json()

    assert [e["type"] for e in snapshot["events"]] == ["model_call", "plan_rejected", "model_call", "plan_proposed"]
    assert snapshot["status"] == "awaiting_approval"
    assert [s["tool"] for s in snapshot["plan"]["steps"]] == ["audit_population"]


def test_exhausting_the_budget_returns_the_completed_evidence_plus_open_questions(scenarios):
    investigation_id, events = run(scenarios, BUDGET)

    assert len(of_type(events, "tool_started")) == 12
    assert len(of_type(events, "tool_finished")) == 12
    [exhausted] = of_type(events, "budget_exhausted")
    assert (exhausted["tool_calls_used"], exhausted["max_tool_calls"]) == (12, 12)
    over = [r for d in of_type(events, "agent_decision") for r in d["requests"] if r["status"] == "over_budget"]
    assert over, "the agent asked for more than the budget allowed"
    sources = {q["source"] for q in exhausted["open_questions"]}
    assert "over_budget_request" in sources
    assert {q["request_id"] for q in exhausted["open_questions"] if q["source"] == "over_budget_request"} == {r["request_id"] for r in over}
    assert len(of_type(events, "claim_drafted")) == 1
    assert events[-1]["type"] == "package_ready"
    assert events[-1]["package"]["open_questions"] == exhausted["open_questions"]
    package = zipfile.ZipFile(io.BytesIO(scenarios.get(f"/api/investigations/{investigation_id}/package").content))
    assert json.loads(package.read("manifest.json"))["open_questions"] == exhausted["open_questions"]


def test_invalid_follow_up_requests_are_rejected_with_their_reasons_and_never_run(scenarios):
    _, events = run(scenarios, INVALID)

    assert [e["tool"] for e in of_type(events, "tool_started")] == ["audit_population"]
    [decision] = of_type(events, "agent_decision")
    statuses = [(r["tool"], r["status"]) for r in decision["requests"]]
    assert statuses == [
        ("resegment_with_proseg", "rejected"),
        ("run_random_thinning_control", "rejected"),
        ("run_label_sensitivity_check", "rejected"),
        ("audit_population", "rejected"),
    ]
    reasons = [r["rejection_reason"] for r in decision["requests"]]
    assert "not a tool in the registry" in reasons[0]
    assert "obs-9" in reasons[1]
    assert "made-up-rule" in reasons[2]
    assert "already ran as obs-1" in reasons[3]
    assert decision["open_questions"] == ["Would re-segmentation change the podocyte LRP2 count?"]


def test_the_researcher_can_reject_a_plan_and_nothing_runs(scenarios):
    investigation_id = ask(scenarios, HERO)

    first = scenarios.post(f"/api/investigations/{investigation_id}/reject").json()
    second = scenarios.post(f"/api/investigations/{investigation_id}/reject").json()
    after_approve = approve(scenarios, investigation_id)

    assert first["status"] == second["status"] == after_approve["status"] == "rejected"
    assert first["plan"]["status"] == "rejected"
    assert [e["type"] for e in after_approve["events"]] == ["model_call", "plan_proposed", "plan_rejected"]
    assert after_approve["events"][-1]["by"] == "researcher"


def test_a_claim_draft_citing_a_number_the_finding_does_not_hold_is_redrafted_once_then_rejected(tmp_path):
    bad = json.dumps({
        "text": "Nucleus-only assignment keeps 3 of the 4 LRP2 molecules in cells labelled Podocyte.",
        "cited": {"kept": {"value": 3, "source": "sections[SYN-01].conditions[nucleus_only].molecules"},
                  "default": {"value": 4, "source": "sections[SYN-01].conditions[default].molecules"}},
    })
    providers = FakeProviders(answers={"meta-models/muse-spark-open": [bad, bad]})
    with TestClient(live_app(tmp_path, providers)) as client:
        _, events = run_live(client)

    assert [e["call"]["purpose"] for e in of_type(events, "model_call")] == ["plan", "follow_up", "claim_draft", "claim_redraft"]
    [rejected] = of_type(events, "claim_rejected")
    assert any("is 3, but sections[SYN-01].conditions[nucleus_only].molecules is 0" in p for p in rejected["problems"])
    assert of_type(events, "claim_drafted") == []
    assert events[-1]["type"] == "package_ready"


def test_a_claim_draft_that_is_not_valid_json_even_after_repair_rejects_that_claim_and_the_run_still_completes(tmp_path):
    providers = FakeProviders(answers={"meta-models/muse-spark-open": ["{\"text\": \"cut off", "{\"text\": \"cut off again"]})
    with TestClient(live_app(tmp_path, providers)) as client:
        _, events = run_live(client)

    [rejected] = of_type(events, "claim_rejected")
    assert "does not match ClaimDraft" in rejected["problems"][0]
    assert events[-1]["type"] == "package_ready"


def test_a_claim_may_state_the_frozen_threshold_without_citing_it(tmp_path):
    draft = json.dumps({
        "text": "In cells labelled Podocyte by construction, nucleus-only assignment keeps 0 of the 4 LRP2 molecules, "
        "compared against the home-matched expectation × 2^-0.5.",
        "cited": {"kept": {"value": 0, "source": "sections[SYN-01].conditions[nucleus_only].molecules"},
                  "default": {"value": 4, "source": "sections[SYN-01].conditions[default].molecules"}},
    })
    providers = FakeProviders(answers={"meta-models/muse-spark-open": draft})
    with TestClient(live_app(tmp_path, providers)) as client:
        _, events = run_live(client)

    assert [e["call"]["purpose"] for e in of_type(events, "model_call") if e["call"]["purpose"] != "visual_check"] == [
        "plan", "follow_up", "claim_draft"]
    assert len(of_type(events, "claim_drafted")) == 1


TWO_PART = ("My hypothesis: the podocytes this atlas calls 'endocytic' really carry LRP2, and the UMOD seen in B cells is "
            "spillover from neighbouring thick ascending limb cells. Does each part hold up under stricter assignment?")


def test_the_recorded_two_part_hypothesis_replays_with_verdicts_that_follow_the_rule_from_its_own_claims(client):
    """The live golden-path run, as immutable replay. Checks that each streamed verdict is what the frozen rule gives
    for the streamed claims, never what the outcome is (ADR-0001)."""
    from spatialscout.contracts import Claim, SubClaim
    from spatialscout.verify.verdict import derive_verdicts

    snapshot = client.post("/api/investigations", json={"question": TWO_PART, "run_mode": "immutable_replay"}).json()
    events = snapshot["events"]
    assert (snapshot["run_mode"], snapshot["replay"]["origin"], snapshot["status"]) == ("immutable_replay", "live", "complete")
    [verdict] = of_type(events, "verdict")
    subs = [SubClaim.model_validate(v["sub_claim"]) for v in verdict["verdict"]["verdicts"]]
    assert len(subs) == 2
    claims = [Claim.model_validate(e["claim"]) for e in of_type(events, "claim_verified") if not e["claim"]["injected"]["is_injected"]]
    populations = {e["artifact_id"]: None for e in of_type(events, "tool_finished")}
    started = {e["observation_id"]: e for e in of_type(events, "tool_started")}
    for finished in of_type(events, "tool_finished"):
        arguments = started[finished["observation_id"]]["arguments"]
        if finished["tool"] == "audit_population":
            populations[finished["artifact_id"]] = (arguments["cell_type"], arguments["genes"])
    populations = {k: v for k, v in populations.items() if v is not None}
    expected = derive_verdicts(subs, claims, populations, dataset_id=snapshot["dataset_id"])
    assert [v.model_dump(mode="json") for v in expected] == verdict["verdict"]["verdicts"]
