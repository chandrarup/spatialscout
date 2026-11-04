"""Write the hand-authored stored model responses that seam-2 tests (and the walking skeleton) play back.

No model is called. Each scenario runs the real orchestrator on the synthetic section, in live mode, against a mock
transport whose answers are written below by hand (a "policy" per scenario). Every answer is built from the request
the orchestrator actually sends, so every number in it comes from a computed artifact (ADR-0001), and every cache key
is the orchestrator's own. The live responses are then saved as a recording marked `origin: hand_authored`.

Scenarios (one recording each, keyed by its question; all but the skeleton go to fixtures/agent_scenarios/):
- syn01-podocyte-lrp2: the walking skeleton. The agent reads the audit and requests no control (a skipped control).
- syn01-hero-lrp2-cubn: the hero question on SYN-01. The agent requests the random-thinning control and the
  label-sensitivity check, each citing obs-1, and the claim cites both.
- syn01-unsupported-plan: both the plan and the re-plan name a tool that is not in the registry.
- syn01-replan: the plan names a tool that is not in the registry; the re-plan uses audit_population.
- syn01-budget: the agent keeps requesting follow-ups until the 12-call budget is spent.
- syn01-invalid-follow-ups: the agent requests an unknown tool, cites an observation that does not exist, and passes
  invalid arguments; none of them runs.

Rerun after changing a prompt, a tool, a response schema or the synthetic section (`make fixtures` does):

    uv run python scripts/build_skeleton_recording.py

The live GSE286184 hero recording (`fixtures/recordings/gse286184-hero-*`) is never touched here: it holds real
model responses and needs the ingested tables (see scripts/record_live_investigation.py).
"""

import asyncio
import json

import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx2 as httpx

from spatialscout.agent import DEFAULT_REGISTRY, Orchestrator
from spatialscout.contracts import TERMINAL_STATUSES, InvestigationStatus, Recording
from spatialscout.data import DatasetStore
from spatialscout.gateway import LIST_PRICES, ApiKeys, RecordingLibrary
from spatialscout.gateway.gate import LiveGate
from spatialscout.settings import Settings

PASSCODE = "hand-authored"
SKELETON = "syn01-podocyte-lrp2"
# The other scenarios are for tests only, kept out of fixtures/recordings/ so the web app never offers their
# questions as examples. Seam-2 agent-loop tests point the recordings directory here.
SCENARIOS_DIR = "agent_scenarios"
SECTION = "SYN-01"
DEFAULT_RULE, ALTERNATIVE_RULE = "synthetic-by-construction", "synthetic-alternative"

Policy = Callable[[dict[str, Any]], dict[str, Any]]
"""Given a chat request body, the JSON object to answer with."""


def payload(body: dict[str, Any]) -> dict[str, Any]:
    """The JSON payload of the request's first user message."""
    return json.loads(next(m["content"] for m in body["messages"] if m["role"] == "user"))


def is_retry(body: dict[str, Any]) -> bool:
    """A re-plan or redraft: the conversation carries the rejected answer and the feedback."""
    return len(body["messages"]) > 2


def audit_step(genes: list[str], rationale: str, cell_type: str = "Podocyte", rule: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {"section_ids": [SECTION], "cell_type": cell_type, "genes": genes, "conditions": ["default", "nucleus_only"]}
    if rule:
        arguments["label_rule_id"] = rule
    return {"tool": "audit_population", "arguments": arguments, "rationale": rationale}


def plan(summary: str, steps: list[dict[str, Any]], cell_types: list[str], sub_claims: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"summary": summary, "contrast": None, "cell_types": cell_types, "conditions": ["default", "nucleus_only"], "steps": steps,
            "sub_claims": sub_claims or []}


def sub_claim(text: str, genes: list[str], predicted: str, cell_type: str = "Podocyte") -> dict[str, Any]:
    """The prediction the question states (the researcher's hypothesis), never an outcome."""
    return {"text": text, "cell_type": cell_type, "genes": genes, "predicted": predicted}


def unsupported_step() -> dict[str, Any]:
    return {"tool": "resegment_with_proseg", "arguments": {"section_ids": [SECTION]},
            "rationale": "Re-segmenting the section would show whether the assignment itself changes the answer."}


def no_follow_up(reading: str) -> dict[str, Any]:
    return {"reading": reading, "requests": [], "open_questions": []}


def claim(body: dict[str, Any]) -> dict[str, Any]:
    """The hand-authored claim. Every number is read from the finding and controls in the request (ADR-0001)."""
    data = payload(body)
    finding, controls = data["finding"], data.get("controls", [])
    section = finding["sections"][0]
    by_condition = {value["condition"]: value for value in section["conditions"]}
    default, strict = by_condition["default"], by_condition["nucleus_only"]
    where = f"sections[{section['section_id']}]"
    genes = " or ".join(finding["genes"])
    cell_type = finding["population"]["cell_type"]
    text = (
        f"In synthetic section {section['section_id']}, nucleus-only assignment keeps {strict['molecules']} of the "
        f"{default['molecules']} {genes} molecules that the default condition counts toward the "
        f"{section['cells_labelled']} cells labelled {cell_type} by construction (retention {strict['retention']:.0%})."
    )
    cited = {
        "cells_labelled": {"value": section["cells_labelled"], "source": f"{where}.cells_labelled"},
        "molecules_default": {"value": default["molecules"], "source": f"{where}.conditions[default].molecules"},
        "molecules_nucleus_only": {"value": strict["molecules"], "source": f"{where}.conditions[nucleus_only].molecules"},
        "retention_nucleus_only": {"value": strict["retention"], "source": f"{where}.conditions[nucleus_only].retention"},
    }
    for control in controls:
        if control["control_kind"] == "label_sensitivity":
            other = control["arms"][1]
            text += (
                f" The label-sensitivity check labels {other['cells_labelled']} cells {cell_type} under the "
                f"{other['label_rule_id']} rule, so the population depends on the label rule."
            )
            cited["cells_labelled_other_rule"] = {
                "value": other["cells_labelled"],
                "source": f"controls[{control['control_id']}].arms[{other['label_rule_id']}].cells_labelled",
            }
    return {"text": text, "cited": cited}


def visual(body: dict[str, Any]) -> dict[str, Any]:
    """The hand-authored visual check. No model reads the figure here, so it reports no disagreement of its own: it
    restates the direction and pattern the request says the claim states, and says that nobody looked."""
    user = next(m for m in body["messages"] if m["role"] == "user")
    data = json.loads(next(part["text"] for part in user["content"] if part["type"] == "text"))
    stated = data.get("claim_states_direction") or ""
    return {
        "panel_a_direction": "holds" if "holds" in stated else "drops" if "drops" in stated else "unclear",
        "panel_a_matches_claim": True,
        "single_section_drives_panel_a": False,
        "panel_b_matches_claim": True if data.get("claim_states_neighbour_pattern") else None,
        "explanation": "Hand-authored response for tests: no model read this figure.",
    }


def is_visual(body: dict[str, Any]) -> bool:
    return any(isinstance(m["content"], list) for m in body["messages"])


def by_model(planner: Policy, agent: Policy, drafter: Policy = claim) -> Policy:
    def answer(body: dict[str, Any]) -> dict[str, Any]:
        if is_visual(body):
            return visual(body)
        if body["model"] == "muse-wonder-1.0":
            return planner(body)
        if body["model"] == "muse-spark-1.3":
            return agent(body)
        return drafter(body)

    return answer


# --- scenarios ---------------------------------------------------------------------------------------------


def skeleton() -> Policy:
    return by_model(
        lambda body: plan(
            "Audit LRP2 in cells labelled Podocyte in synthetic section SYN-01 under the default and nucleus-only conditions.",
            [audit_step(["LRP2"], "The capability report supports an assignment audit, and nucleus-only is the stricter condition the question names.")],
            ["Podocyte"],
            [sub_claim("Podocyte LRP2 survives nucleus-only assignment.", ["LRP2"], "holds")],
        ),
        lambda body: no_follow_up(
            "Nucleus-only assignment keeps none of the podocyte LRP2 molecules. The question asks only whether they survive, "
            "so I request no control; any claim about assignment sensitivity will lack one."
        ),
    )


def hero() -> Policy:
    def agent(body: dict[str, Any]) -> dict[str, Any]:
        data = payload(body)
        inspected = next(o for o in data["observations"] if o["observation_id"] == data["read_now"])
        if inspected["origin"] != "plan":
            return no_follow_up(f"{inspected['observation_id']} is the control I asked for; it needs no further control.")
        arguments = inspected["arguments"]
        return {
            "reading": f"{inspected['observation_id']} shows the podocyte LRP2/CUBN molecules dropping under nucleus-only "
            "assignment, and the podocytes are labelled by a rule that could involve these genes.",
            "requests": [
                {"tool": "run_random_thinning_control", "arguments": arguments, "cites_observation": inspected["observation_id"],
                 "reason": "The retention drop must be compared with what random molecule loss at the matched rate gives."},
                {"tool": "run_label_sensitivity_check", "arguments": {**arguments, "label_rule_ids": [DEFAULT_RULE, ALTERNATIVE_RULE]},
                 "cites_observation": inspected["observation_id"],
                 "reason": "The population is defined by a label rule; the result must be compared under a second rule."},
            ],
            "open_questions": [],
        }

    return by_model(
        lambda body: plan(
            "Audit LRP2 or CUBN presence in cells labelled Podocyte in SYN-01 under the default and nucleus-only conditions.",
            [audit_step(["LRP2", "CUBN"], "The question asks whether podocyte LRP2/CUBN survives a stricter assignment.", rule=DEFAULT_RULE)],
            ["Podocyte"],
            [sub_claim("Podocytes really carry LRP2 and CUBN.", ["LRP2", "CUBN"], "holds")],
        ),
        agent,
    )


def unsupported() -> Policy:
    return by_model(
        lambda body: plan("Re-segment SYN-01 with Proseg, then recount podocyte LRP2.", [unsupported_step()], ["Podocyte"]),
        lambda body: no_follow_up("unused"),
    )


def replan() -> Policy:
    def planner(body: dict[str, Any]) -> dict[str, Any]:
        if not is_retry(body):
            return plan("Re-segment SYN-01 with Proseg, then recount podocyte LRP2.", [unsupported_step()], ["Podocyte"])
        return plan(
            "Re-segmentation is not available, so audit LRP2 in cells labelled Podocyte under default and nucleus-only.",
            [audit_step(["LRP2"], "The registry has no re-segmentation tool; an assignment audit is the supported alternative.")],
            ["Podocyte"],
        )

    return by_model(planner, lambda body: no_follow_up("The audit answers the question as asked; I request no control."))


BUDGET_CALLS = [(cell_type, gene) for cell_type, gene in [
    ("Endothelial", "PECAM1"), ("Mesangial", "PDGFRB"), ("PT", "LRP2"), ("PT", "CUBN"), ("TAL", "UMOD"), ("T cell", "CD3D"),
]]


def budget() -> Policy:
    """After every audit the agent asks for both of its controls, and after every observation for the audits of the
    next two populations, so its requests outrun the budget."""

    def agent(body: dict[str, Any]) -> dict[str, Any]:
        data = payload(body)
        inspected = next(o for o in data["observations"] if o["observation_id"] == data["read_now"])
        ran = [(o["tool"], json.dumps(o["arguments"], sort_keys=True)) for o in data["observations"]]
        requests = []
        if inspected["tool"] == "audit_population":
            requests.append({"tool": "run_random_thinning_control", "arguments": inspected["arguments"], "cites_observation": inspected["observation_id"],
                             "reason": f"{inspected['observation_id']} reports a drop that needs its random-thinning control."})
            requests.append({"tool": "run_label_sensitivity_check",
                             "arguments": {**inspected["arguments"], "label_rule_ids": [DEFAULT_RULE, ALTERNATIVE_RULE]},
                             "cites_observation": inspected["observation_id"],
                             "reason": f"{inspected['observation_id']} depends on a label rule; compare it under the alternative rule."})
        for cell_type, gene in BUDGET_CALLS:
            arguments = audit_step([gene], "", cell_type)["arguments"]
            if ("audit_population", json.dumps(arguments, sort_keys=True)) not in ran:
                requests.append({"tool": "audit_population", "arguments": arguments, "cites_observation": inspected["observation_id"],
                                 "reason": f"After {inspected['observation_id']}, the next population to audit is {gene} in {cell_type} cells."})
                if sum(r["tool"] == "audit_population" for r in requests) == 2:
                    break
        return {"reading": f"{inspected['observation_id']}: {inspected.get('summary', '')[:120]}", "requests": requests,
                "open_questions": []}

    return by_model(
        lambda body: plan(
            "Audit NPHS1 in cells labelled Podocyte, then follow the other populations as the agent sees fit.",
            [audit_step(["NPHS1"], "Start with the podocyte marker the question names.")],
            ["Podocyte"],
        ),
        agent,
    )


def invalid_follow_ups() -> Policy:
    def agent(body: dict[str, Any]) -> dict[str, Any]:
        data = payload(body)
        arguments = data["observations"][0]["arguments"]
        return {
            "reading": "obs-1 shows the podocyte LRP2 drop.",
            "requests": [
                {"tool": "resegment_with_proseg", "arguments": {"section_ids": [SECTION]}, "cites_observation": "obs-1",
                 "reason": "Re-segmenting would settle it."},
                {"tool": "run_random_thinning_control", "arguments": arguments, "cites_observation": "obs-9",
                 "reason": "The drop needs its control."},
                {"tool": "run_label_sensitivity_check", "arguments": {**arguments, "label_rule_ids": [DEFAULT_RULE, "made-up-rule"]},
                 "cites_observation": "obs-1", "reason": "Compare under another rule."},
                {"tool": "audit_population", "arguments": arguments, "cites_observation": "obs-1", "reason": "Run it again."},
            ],
            "open_questions": ["Would re-segmentation change the podocyte LRP2 count?"],
        }

    return by_model(
        lambda body: plan(
            "Audit LRP2 in cells labelled Podocyte in SYN-01 under the default and nucleus-only conditions.",
            [audit_step(["LRP2"], "An assignment audit answers whether podocyte LRP2 survives nucleus-only assignment.")],
            ["Podocyte"],
        ),
        agent,
    )


SCENARIOS: dict[str, tuple[str, Callable[[], Policy], str]] = {
    "syn01-podocyte-lrp2": (
        "Does podocyte LRP2 in the synthetic section survive nucleus-only assignment?", skeleton,
        "Hand-authored model responses for the walking skeleton; the agent requests no control. No model was called.",
    ),
    "syn01-hero-lrp2-cubn": (
        "Do the podocytes in the synthetic section really carry LRP2 and CUBN, or is that segmentation?", hero,
        "Hand-authored model responses: the agent requests the random-thinning control and the label-sensitivity check. No model was called.",
    ),
    "syn01-unsupported-plan": (
        "Re-segment the synthetic section with Proseg and recount podocyte LRP2.", unsupported,
        "Hand-authored model responses: the plan and the re-plan both name a tool outside the registry. No model was called.",
    ),
    "syn01-replan": (
        "Would re-segmenting the synthetic section change podocyte LRP2?", replan,
        "Hand-authored model responses: the first plan names a tool outside the registry, the re-plan does not. No model was called.",
    ),
    "syn01-budget": (
        "Which synthetic cell populations keep their marker molecules under nucleus-only assignment?", budget,
        "Hand-authored model responses: the agent keeps requesting follow-ups until the budget is spent. No model was called.",
    ),
    "syn01-invalid-follow-ups": (
        "Is podocyte LRP2 in the synthetic section an assignment effect?", invalid_follow_ups,
        "Hand-authored model responses: every follow-up the agent requests is invalid, so none runs. No model was called.",
    ),
}


class MockProviders:
    """Answers chat completions with a policy's JSON, as the providers' chat-completions bodies do."""

    def __init__(self, policy: Policy) -> None:
        self._policy = policy

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        content = json.dumps(self._policy(body))
        return httpx.Response(200, json={
            "id": "chatcmpl-hand-authored", "object": "chat.completion", "model": body["model"],
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
        })


async def wait_for(investigation, statuses) -> None:
    for _ in range(1200):
        if investigation.state.status in statuses:
            return
        await asyncio.sleep(0.05)
    raise TimeoutError(f"{investigation.investigation_id} stuck at {investigation.state.status}")


async def build(recording_id: str, question: str, policy: Policy, note: str, settings: Settings) -> Path:
    with tempfile.TemporaryDirectory() as scratch:
        gate = LiveGate(
            passcode=PASSCODE, daily_budget_usd=1000.0, spend_dir=Path(scratch) / "spend",
            keys=ApiKeys({"meta": "hand-authored", "baseten": "hand-authored", "fireworks": "hand-authored"}),
            clock=lambda: datetime.now(UTC), prices=LIST_PRICES, transport=httpx.MockTransport(MockProviders(policy)),
        )
        orchestrator = Orchestrator(
            store=DatasetStore(settings.fixtures_dir), recordings=RecordingLibrary(Path(scratch) / "none"), registry=DEFAULT_REGISTRY,
            investigations_dir=Path(scratch) / "investigations", dataset_id=settings.dataset_id, live_gate=gate,
        )
        investigation = orchestrator.start(question, "live", passcode=PASSCODE)
        await wait_for(investigation, {InvestigationStatus.AWAITING_APPROVAL, *TERMINAL_STATUSES})
        orchestrator.approve(investigation.investigation_id)
        await wait_for(investigation, TERMINAL_STATUSES)
        await orchestrator.shutdown()
        recorded = Recording.model_validate_json((investigation.directory / "recording.json").read_text(encoding="utf-8"))
    info = recorded.info.model_copy(update={
        "recording_id": recording_id, "recorded_at": datetime.now(UTC).replace(microsecond=0), "origin": "hand_authored", "note": note,
        "dataset_id": None,
    })
    calls = [call.model_copy(update={"response": call.response.model_copy(update={"usage": None}), "latency_ms": None}) for call in recorded.calls]
    directory = settings.recordings_dir if recording_id == SKELETON else settings.fixtures_dir / SCENARIOS_DIR
    path = directory / recording_id / "recording.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(Recording(info=info, calls=calls).model_dump_json(indent=1) + "\n", encoding="utf-8")
    print(f"{recording_id}: {len(calls)} stored responses, run ended {investigation.state.status.value}")
    return path


def main() -> None:
    settings = Settings.from_env()
    for recording_id, (question, policy, note) in SCENARIOS.items():
        asyncio.run(build(recording_id, question, policy(), note, settings))


if __name__ == "__main__":
    main()
