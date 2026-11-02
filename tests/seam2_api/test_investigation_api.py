"""Seam 2: an investigation driven through the HTTP/SSE API on recorded model responses."""

import io
import json
import zipfile

from .conftest import RECORDED_QUESTION


def start(client, question=RECORDED_QUESTION):
    """Post a question and return the investigation once planning has finished."""
    response = client.post("/api/investigations", json={"question": question})
    assert response.status_code == 201, response.text
    investigation_id = response.json()["investigation_id"]
    events = read_events(client, investigation_id, until={"plan_proposed", "error"})
    assert events, "no event arrived"
    return client.get(f"/api/investigations/{investigation_id}").json()


def read_events(client, investigation_id, after_seq=0, until=frozenset({"package_ready", "error"})):
    """Read the SSE stream until an event whose type is in `until`, then disconnect."""
    events = []
    with client.stream("GET", f"/api/investigations/{investigation_id}/events", params={"after_seq": after_seq}) as stream:
        for line in stream.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line.removeprefix("data:")))
                if events[-1]["type"] in until:
                    break
    return events


def test_a_question_gets_the_recorded_plan_and_nothing_runs_before_approval(client):
    investigation = start(client)

    assert investigation["status"] == "awaiting_approval"
    assert [step["tool"] for step in investigation["plan"]["steps"]] == ["audit_population"]
    assert [event["type"] for event in investigation["events"]] == ["plan_proposed"]


def test_a_question_without_stored_responses_fails_instead_of_calling_a_model(client):
    investigation = start(client, "Is UMOD higher in B cells in DKD?")

    assert investigation["status"] == "failed"
    assert investigation["plan"] is None
    last = investigation["events"][-1]
    assert (last["type"], last["code"]) == ("error", "replay_miss")


FULL_SEQUENCE = ["plan_proposed", "plan_approved", "tool_started", "tool_finished", "claim_drafted", "package_ready"]


def approve(client, investigation_id):
    response = client.post(f"/api/investigations/{investigation_id}/approve")
    assert response.status_code == 200, response.text
    return response.json()


def test_an_approved_plan_streams_through_to_an_evidence_package(client):
    investigation_id = start(client)["investigation_id"]
    approve(client, investigation_id)

    events = read_events(client, investigation_id)

    assert [event["type"] for event in events] == FULL_SEQUENCE
    assert [event["seq"] for event in events] == [1, 2, 3, 4, 5, 6]
    assert client.get(f"/api/investigations/{investigation_id}").json()["status"] == "complete"


def test_the_claim_cites_the_audit_result_with_the_answers_known_by_construction(client):
    investigation_id = start(client)["investigation_id"]
    approve(client, investigation_id)
    claim = next(event["claim"] for event in read_events(client, investigation_id) if event["type"] == "claim_drafted")

    assert claim["finding"]["finding_kind"] == "audit"
    cited = {number["source"]: number["value"] for number in claim["cited"].values()}
    # 3 podocytes; all 4 of their LRP2 molecules lie in C03's expansion zone, so nucleus-only keeps none.
    assert cited == {
        "sections[SYN-01].cells_labelled": 3,
        "sections[SYN-01].conditions[default].molecules": 4,
        "sections[SYN-01].conditions[nucleus_only].molecules": 0,
        "sections[SYN-01].conditions[nucleus_only].retention": 0.0,
    }
    assert (claim["evidence_status"], claim["verification_status"], claim["review_status"]) == (
        "insufficient_evidence", "pending", "unreviewed",
    )


def test_refreshing_at_approval_loses_no_events(client):
    investigation_id = start(client)["investigation_id"]  # the page saw plan_proposed (seq 1), then reloaded
    approve(client, investigation_id)

    after_refresh = read_events(client, investigation_id, after_seq=1)

    assert [event["type"] for event in after_refresh] == FULL_SEQUENCE[1:]


def test_approving_twice_runs_the_plan_once(client):
    investigation_id = start(client)["investigation_id"]
    approve(client, investigation_id)
    second = approve(client, investigation_id)
    read_events(client, investigation_id)
    after_finish = approve(client, investigation_id)

    assert second["plan"]["status"] == "approved"
    assert after_finish["status"] == "complete"
    assert [event["type"] for event in after_finish["events"]] == FULL_SEQUENCE


def test_reconnecting_mid_execution_with_after_seq_delivers_exactly_the_missing_events(client):
    investigation_id = start(client)["investigation_id"]
    approve(client, investigation_id)

    before_drop = read_events(client, investigation_id, until={"tool_started"})
    after_reconnect = read_events(client, investigation_id, after_seq=before_drop[-1]["seq"])

    assert [event["seq"] for event in before_drop + after_reconnect] == [1, 2, 3, 4, 5, 6]
    assert [event["type"] for event in before_drop + after_reconnect] == FULL_SEQUENCE


def run_to_package(client):
    investigation_id = start(client)["investigation_id"]
    approve(client, investigation_id)
    read_events(client, investigation_id)
    response = client.get(f"/api/investigations/{investigation_id}/package")
    assert response.status_code == 200, response.text
    return zipfile.ZipFile(io.BytesIO(response.content))


def verify_chain(client, audit_log_jsonl):
    response = client.post("/api/audit-log/verify", content=audit_log_jsonl, headers={"content-type": "text/plain"})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_package_holds_the_claims_the_audit_log_and_a_manifest_with_the_head_hash(client):
    package = run_to_package(client)

    assert sorted(package.namelist()) == ["audit_log.jsonl", "claims.json", "manifest.json"]
    manifest = json.loads(package.read("manifest.json"))
    last_entry = json.loads(package.read("audit_log.jsonl").decode().splitlines()[-1])
    assert manifest["audit_log"]["head_hash"] == last_entry["entry_hash"]
    assert (manifest["run_mode"], manifest["review_state"]) == ("cached_tool_rerun", "work_in_progress")
    assert [claim["finding"]["finding_kind"] for claim in json.loads(package.read("claims.json"))] == ["audit"]


def test_the_exported_audit_log_passes_its_chain_check(client):
    package = run_to_package(client)

    result = verify_chain(client, package.read("audit_log.jsonl").decode())

    assert result["ok"] is True
    assert result["head_hash"] == json.loads(package.read("manifest.json"))["audit_log"]["head_hash"]


def test_editing_any_entry_of_the_exported_audit_log_fails_the_chain_check_at_that_entry(client):
    lines = run_to_package(client).read("audit_log.jsonl").decode().splitlines()

    for index, line in enumerate(lines):
        entry = json.loads(line)
        entry["recorded_at"] = "2026-01-01T00:00:00+00:00"  # an edit, left un-rehashed
        edited = [*lines[:index], json.dumps(entry), *lines[index + 1:]]

        result = verify_chain(client, "\n".join(edited) + "\n")

        assert (result["ok"], result["first_bad_seq"]) == (False, index + 1)
