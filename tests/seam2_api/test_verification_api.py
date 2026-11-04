"""Seam 2: claim verification through the HTTP/SSE API, as cached tool reruns on hand-authored recordings.

The walking skeleton's agent skips every control, so its claim must fail structurally with "required control not
run"; the injected variant shown in the stream must end failed or disputed, with its reason in the event stream and
in the audit log; and "Challenge the verifier" serves the recorded variants by error kind, with no model call.
"""

import io
import json
import time
import zipfile

from spatialscout.contracts import InjectedErrorKind

from .conftest import RECORDED_QUESTION
from .test_agent_loop import of_type
from .test_investigation_api import approve, read_events


def run(client):
    investigation_id = client.post("/api/investigations", json={"question": RECORDED_QUESTION}).json()["investigation_id"]
    read_events(client, investigation_id, until={"plan_proposed"})
    approve(client, investigation_id)
    return investigation_id, read_events(client, investigation_id)


def audit_entries(client, investigation_id, kind):
    package = zipfile.ZipFile(io.BytesIO(client.get(f"/api/investigations/{investigation_id}/package").content))
    entries = [json.loads(line) for line in package.read("audit_log.jsonl").decode().splitlines()]
    return [entry["payload"] for entry in entries if entry["kind"] == kind]


def test_a_claim_whose_agent_skipped_its_controls_fails_with_required_control_not_run(client):
    _, events = run(client)

    [verified] = [e for e in of_type(events, "claim_verified") if not e["claim"]["injected"]["is_injected"]]
    assert verified["claim"]["verification_status"] == "failed"
    assert verified["verification"]["in_validated_summary"] is False
    structural = next(c for c in verified["verification"]["checks"] if c["kind"] == "structural")
    assert any(r.startswith("required control not run") for r in structural["reasons"])
    # a failed claim stays in history: it was drafted, and it is the same claim
    assert of_type(events, "claim_drafted")[0]["claim"]["claim_id"] == verified["claim"]["claim_id"]


def test_an_injected_error_ends_failed_or_disputed_with_its_reason_in_the_stream_and_the_audit_log(client):
    investigation_id, events = run(client)

    [injected] = [e for e in of_type(events, "claim_verified") if e["claim"]["injected"]["is_injected"]]
    assert injected["claim"]["injected"]["kind"] == "changed_effect"
    assert injected["claim"]["verification_status"] in ("failed", "disputed")
    numerical = next(c for c in injected["verification"]["checks"] if c["kind"] == "numerical")
    reason = next(r for r in numerical["reasons"] if "independent recompute" in r)

    [logged] = [p for p in audit_entries(client, investigation_id, "claim_verified") if p["injected"]["is_injected"]]
    assert logged["claim_id"] == injected["claim"]["claim_id"]
    assert logged["verification_status"] == injected["claim"]["verification_status"]
    assert reason in logged["reasons"]


def test_challenge_the_verifier_serves_every_recorded_variant_by_kind_without_a_model_call(client):
    investigation_id, events = run(client)
    claim_id = of_type(events, "claim_drafted")[0]["claim"]["claim_id"]

    started = time.perf_counter()
    response = client.get(f"/api/investigations/{investigation_id}/claims/{claim_id}/challenges")
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert response.status_code == 200
    challenges = response.json()
    assert [v["kind"] for v in challenges["variants"]] == [k.value for k in InjectedErrorKind]
    for variant in challenges["variants"]:
        assert variant["claim"]["injected"] == {"is_injected": True, "kind": variant["kind"]}
        # the skeleton's claim cites no control, so there is none to remove; every other kind changes the claim
        assert variant["changes"] or variant["kind"] == "missing_required_control"
        assert variant["detected"] == bool(variant["new_reasons"])
    assert elapsed_ms < 100
    assert of_type(read_events(client, investigation_id, after_seq=events[-1]["seq"]), "model_call") == []


def test_challenges_of_an_unknown_claim_are_not_found(client):
    investigation_id, _ = run(client)
    assert client.get(f"/api/investigations/{investigation_id}/claims/clm-nope/challenges").status_code == 404


def test_the_sub_claim_verdict_streams_and_is_logged_and_a_failed_claim_never_confirms_it(client):
    """The skeleton's plan predicts that podocyte LRP2 holds. Its only claim fails structurally (no control was run),
    so the rule makes the sub-claim inconclusive, whatever the evidence label."""
    investigation_id, events = run(client)

    [event] = of_type(events, "verdict")
    [verdict] = event["verdict"]["verdicts"]
    assert verdict["sub_claim"]["predicted"] == "holds" and verdict["sub_claim"]["genes"] == ["LRP2"]
    assert verdict["verdict"] == "inconclusive" and "failed" in verdict["reason"]
    [claim] = [e["claim"] for e in of_type(events, "claim_verified") if not e["claim"]["injected"]["is_injected"]]
    assert verdict["claim_ids"] == [claim["claim_id"]]
    assert "these sections" in event["verdict"]["scope"]

    [logged] = audit_entries(client, investigation_id, "verdict_computed")
    assert logged["verdicts"] == event["verdict"]["verdicts"]


def test_the_run_canvas_reads_each_finding_and_its_checked_figure_from_the_investigation(client):
    investigation_id, events = run(client)
    finding_id = next(e["artifact_id"] for e in of_type(events, "tool_finished") if e["artifact_id"].startswith("fnd-"))

    artifact = client.get(f"/api/investigations/{investigation_id}/artifacts/{finding_id}")
    assert artifact.status_code == 200
    assert artifact.json()["finding_id"] == finding_id

    [verified] = [e for e in of_type(events, "claim_verified") if not e["claim"]["injected"]["is_injected"]]
    figure_finding = verified["verification"]["figure"]["finding_id"]
    figure = client.get(f"/api/investigations/{investigation_id}/figures/{figure_finding}.png")
    assert figure.status_code == 200 and figure.headers["content-type"] == "image/png"
    assert figure.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_artifacts_outside_the_investigation_are_not_served(client):
    investigation_id, _ = run(client)
    for path in ("artifacts/fnd-0000000000000000", "artifacts/state", "artifacts/..%2Fstate", "figures/fnd-0000000000000000.png"):
        assert client.get(f"/api/investigations/{investigation_id}/{path}").status_code == 404
