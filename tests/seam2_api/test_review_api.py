"""Seam 2: review decisions and the evidence package (ticket 11) through the HTTP API, on the recorded walking skeleton.

A decision records the reviewer, the time and the claim version in the audit log; the package is exported again with
it; and the package's notebook runs top to bottom in a clean Python process, using only the package."""

import io
import json
import subprocess
import sys
import zipfile

from .conftest import RECORDED_QUESTION
from .test_agent_loop import of_type
from .test_investigation_api import approve, read_events


def finished(client):
    investigation_id = client.post("/api/investigations", json={"question": RECORDED_QUESTION}).json()["investigation_id"]
    read_events(client, investigation_id, until={"plan_proposed"})
    approve(client, investigation_id)
    events = read_events(client, investigation_id)
    claim_id = of_type(events, "claim_drafted")[0]["claim"]["claim_id"]
    return investigation_id, claim_id


def package_of(client, investigation_id):
    return zipfile.ZipFile(io.BytesIO(client.get(f"/api/investigations/{investigation_id}/package").content))


def notebook_source(package) -> str:
    cells = json.loads(package.read("verify.ipynb"))["cells"]
    return "\n\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")


def run_in_clean_python(folder, source):
    return subprocess.run([sys.executable, "-I", "-c", source], cwd=folder, capture_output=True, text=True, timeout=60)


def test_a_review_decision_is_logged_with_reviewer_time_and_version_and_exported(client):
    investigation_id, claim_id = finished(client)

    response = client.post(f"/api/investigations/{investigation_id}/claims/{claim_id}/review",
                           json={"decision": "needs_investigation", "reviewer": "Dr. Reviewer"})
    assert response.status_code == 200, response.text
    snapshot = response.json()
    [event] = of_type(snapshot["events"], "review_decided")
    decision = event["decision"]
    assert (decision["claim_id"], decision["claim_version"], decision["reviewer"]) == (claim_id, 1, "Dr. Reviewer")
    assert decision["decided_at_utc"] and event["claim"]["review_status"] == "needs_investigation"
    assert snapshot["events"][-1]["type"] == "package_ready"

    package = package_of(client, investigation_id)
    manifest = json.loads(package.read("manifest.json"))
    assert (manifest["review_state"], manifest["reviews"]) == ("reviewed", 1)
    assert json.loads(package.read("reviews.json"))[0]["decision_id"] == decision["decision_id"]
    assert json.loads(package.read("claims.json"))[0]["review_status"] == "needs_investigation"
    entries = [json.loads(line) for line in package.read("audit_log.jsonl").decode().splitlines()]
    [logged] = [e["payload"] for e in entries if e["kind"] == "review_decided"]
    assert logged == decision
    check = client.post("/api/audit-log/verify", content=package.read("audit_log.jsonl")).json()
    assert check["ok"] and check["head_hash"] == manifest["audit_log"]["head_hash"]


def test_the_notebook_runs_top_to_bottom_on_the_package_alone_and_catches_an_edited_log(client, tmp_path):
    investigation_id, claim_id = finished(client)
    client.post(f"/api/investigations/{investigation_id}/claims/{claim_id}/review", json={"decision": "unresolved", "reviewer": "R"})
    package = package_of(client, investigation_id)
    folder = tmp_path / "package"
    package.extractall(folder)

    result = run_in_clean_python(folder, notebook_source(package))
    assert result.returncode == 0, result.stderr
    assert "cited numbers match their artifacts" in result.stdout and "every check passed" in result.stdout
    script = subprocess.run([sys.executable, "-I", "verify_package.py"], cwd=folder, capture_output=True, text=True, timeout=60)
    assert script.returncode == 0, script.stderr

    log = folder / "audit_log.jsonl"
    log.write_text(log.read_text().replace('"reviewer":"R"', '"reviewer":"X"'), encoding="utf-8")
    tampered = run_in_clean_python(folder, notebook_source(package))
    assert tampered.returncode != 0 and "AssertionError" in tampered.stderr


def test_reviews_that_cannot_be_recorded_are_refused(client):
    investigation_id, claim_id = finished(client)
    base = f"/api/investigations/{investigation_id}/claims"
    assert client.post(f"{base}/clm-nope/review", json={"decision": "unresolved", "reviewer": "R"}).status_code == 404
    unconfirmed = client.post(f"{base}/{claim_id}/review", json={"decision": "unresolved", "reviewer": "R", "via": "voice", "confirmed": False})
    assert unconfirmed.status_code == 409
    assert client.post(f"{base}/{claim_id}/review", json={"decision": "maybe", "reviewer": "R"}).status_code == 422

    pending = client.post("/api/investigations", json={"question": RECORDED_QUESTION}).json()["investigation_id"]
    read_events(client, pending, until={"plan_proposed"})
    assert client.post(f"/api/investigations/{pending}/claims/{claim_id}/review", json={"decision": "unresolved", "reviewer": "R"}).status_code == 409
