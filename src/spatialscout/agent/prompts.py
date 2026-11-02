"""Model requests the orchestrator sends, built deterministically from their inputs.

A request's cache key covers its whole content, so requests never contain ids, timestamps or anything else
that changes between runs; changing a prompt here invalidates the stored responses (regenerate them with
`uv run python scripts/build_skeleton_recording.py`).
"""

from collections.abc import Sequence

from ..contracts import (
    AuditResult,
    CacheInput,
    CapabilityReport,
    ChatMessage,
    ClaimDraft,
    ModelRequest,
    PlanProposal,
    ToolSpec,
    canonical_json,
    checksum,
)

PLANNER_MODEL = "muse-wonder-1.0"
CLAIM_DRAFTING_MODEL = "meta-models/muse-spark-open"

PLANNER_INSTRUCTIONS = (
    "You are SpatialScout's planner. Propose the smallest plan that answers the researcher's question, using only "
    "tools in the registry and only analyses the capability report marks as supported. Give each step the tool's "
    "arguments and a one-sentence rationale. Respond with JSON that matches the response schema."
)

CLAIM_INSTRUCTIONS = (
    "You write one claim about one finding for SpatialScout. Word it cautiously and scope it to the population and "
    "its label rule. Use only numbers that appear in the finding, and list every number the text uses in `cited`, "
    "with the finding field it comes from, written like sections[<section_id>].conditions[<condition>].<field>. "
    "Respond with JSON that matches the response schema."
)


def plan_request(question: str, report: CapabilityReport, tools: Sequence[ToolSpec]) -> tuple[ModelRequest, list[CacheInput]]:
    payload = {"question": question, "capability_report": report.model_dump(mode="json"), "tools": [t.model_dump(mode="json") for t in tools]}
    request = ModelRequest(
        provider="meta",
        model=PLANNER_MODEL,
        messages=[ChatMessage(role="system", content=PLANNER_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=PlanProposal.model_json_schema(),
    )
    inputs = [CacheInput(name="capability_report", version=report.schema_version, sha256=checksum(report))]
    inputs += [CacheInput(name=f"tool:{t.name}", version=t.version, sha256=checksum(t)) for t in tools]
    return request, inputs


def claim_request(question: str, finding: AuditResult, tool: ToolSpec) -> tuple[ModelRequest, list[CacheInput]]:
    payload = {"question": question, "finding": finding.model_dump(mode="json")}
    request = ModelRequest(
        provider="baseten",
        model=CLAIM_DRAFTING_MODEL,
        messages=[ChatMessage(role="system", content=CLAIM_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=ClaimDraft.model_json_schema(),
    )
    return request, [CacheInput(name=f"artifact:{tool.name}", version=tool.version, sha256=checksum(finding))]
