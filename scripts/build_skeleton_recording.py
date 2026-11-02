"""Write the stored model responses the walking skeleton plays back in a cached tool rerun.

No model is called. Each response is hand-authored (the recording says so: origin "hand_authored"), and each
request is built by the orchestrator's own request builders, so the cache keys match. Rerun this after
changing a prompt, a tool, a response schema or the synthetic section; the seam-2 tests fail until you do:

    uv run python scripts/build_skeleton_recording.py
"""

from datetime import UTC, datetime

from spatialscout.agent import DEFAULT_REGISTRY, ToolContext
from spatialscout.agent.prompts import claim_request, plan_request
from spatialscout.contracts import (
    AuditResult,
    CitedNumber,
    ClaimDraft,
    ConditionName,
    ModelResponse,
    PlanProposal,
    ProposedStep,
    RecordedCall,
    Recording,
    ReplayInfo,
)
from spatialscout.data import DatasetStore
from spatialscout.gateway import cache_key
from spatialscout.settings import Settings

RECORDING_ID = "syn01-podocyte-lrp2"
QUESTION = "Does podocyte LRP2 in the synthetic section survive nucleus-only assignment?"


def recorded(purpose, request, inputs, output) -> RecordedCall:
    return RecordedCall(
        purpose=purpose,
        cache_key=cache_key(request, inputs),
        request=request,
        inputs=inputs,
        response=ModelResponse(content=output.model_dump_json(), finish_reason="stop", usage=None),
    )


def draft_claim(finding: AuditResult) -> ClaimDraft:
    """The hand-authored claim. Every number is filled in from the computed audit result (ADR-0001)."""
    section = finding.sections[0]
    by_condition = {value.condition: value for value in section.conditions}
    default, strict = by_condition[ConditionName.DEFAULT], by_condition[ConditionName.NUCLEUS_ONLY]
    where = f"sections[{section.section_id}]"
    text = (
        f"In synthetic section {section.section_id}, nucleus-only assignment keeps {strict.molecules} of the "
        f"{default.molecules} {finding.genes[0]} molecules that the default condition counts toward the "
        f"{section.cells_labelled} cells labelled {finding.population.cell_type} by construction "
        f"(retention {strict.retention:.0%})."
    )
    return ClaimDraft(
        text=text,
        cited={
            "cells_labelled": CitedNumber(value=section.cells_labelled, source=f"{where}.cells_labelled"),
            "molecules_default": CitedNumber(value=default.molecules, source=f"{where}.conditions[default].molecules"),
            "molecules_nucleus_only": CitedNumber(value=strict.molecules, source=f"{where}.conditions[nucleus_only].molecules"),
            "retention_nucleus_only": CitedNumber(value=strict.retention, source=f"{where}.conditions[nucleus_only].retention"),
        },
    )


def main() -> None:
    settings = Settings.from_env()
    store = DatasetStore(settings.fixtures_dir)
    request, inputs = plan_request(QUESTION, store.capability_report(settings.dataset_id), DEFAULT_REGISTRY.specs())
    proposal = PlanProposal(
        summary="Audit LRP2 in cells labelled Podocyte in synthetic section SYN-01 under the default and nucleus-only conditions.",
        contrast=None,
        cell_types=["Podocyte"],
        conditions=[ConditionName.DEFAULT, ConditionName.NUCLEUS_ONLY],
        steps=[
            ProposedStep(
                tool="audit_population",
                arguments={"section_ids": ["SYN-01"], "cell_type": "Podocyte", "genes": ["LRP2"], "conditions": ["default", "nucleus_only"]},
                rationale="The capability report supports an assignment audit, and nucleus-only is the stricter condition the question names.",
            )
        ],
    )
    calls = [recorded("plan", request, inputs, proposal)]
    tool = DEFAULT_REGISTRY.get("audit_population")
    finding = tool.run(tool.arguments.model_validate(proposal.steps[0].arguments), ToolContext(store=store))
    request, inputs = claim_request(QUESTION, finding, tool.spec())
    calls.append(recorded("claim_draft", request, inputs, draft_claim(finding)))
    recording = Recording(
        info=ReplayInfo(
            recording_id=RECORDING_ID,
            recorded_at=datetime.now(UTC).replace(microsecond=0),
            origin="hand_authored",
            question=QUESTION,
            note="Hand-authored model responses for the walking skeleton (ticket 01); no model was called.",
        ),
        calls=calls,
    )
    path = settings.recordings_dir / RECORDING_ID / "recording.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(recording.model_dump_json(indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(calls)} stored responses to {path}")


if __name__ == "__main__":
    main()
