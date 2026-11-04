"""Model requests the orchestrator sends, built deterministically from their inputs.

A request's cache key covers its whole content, so requests never contain investigation ids, timestamps or anything
else that changes between runs: observations are numbered `obs-<n>` and requests `req-<n>` in the order they happen,
and artifacts are named by their content ids. Changing a prompt here invalidates the stored responses; regenerate them
with `make fixtures`.

- plan: Muse Wonder proposes a plan from the question, the dataset, its capability report and the plannable tools;
- replan: the same conversation, the rejected proposal and the reason, for the one re-plan allowed;
- follow-up: Muse Spark 1.3 reads one observation and may request follow-up tools, each citing an observation;
- claim: Muse Spark Open drafts one claim about one audit result, with the controls the agent ran for it;
- redraft: the same conversation, the rejected draft and its problems, for the one redraft allowed.
"""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from ..contracts import (
    AuditResult,
    CacheInput,
    CapabilityReport,
    ChatMessage,
    ClaimDraft,
    DatasetManifest,
    FollowUpDecision,
    LabelRuleSet,
    ModelRequest,
    Plan,
    PlanProposal,
    ToolSpec,
    canonical_json,
    checksum,
    sha256_hex,
)

PLANNER_MODEL = "muse-wonder-1.0"
AGENT_MODEL = "muse-spark-1.3"
CLAIM_DRAFTING_MODEL = "meta-models/muse-spark-open"

PLANNER_INSTRUCTIONS = (
    "You are SpatialScout's planner. Propose the smallest plan that answers the researcher's question, using only "
    "the tools listed and only analyses the capability report marks as supported. Give each step the tool's "
    "arguments, valid against its arguments_schema, and a one-sentence rationale; use the dataset's own section ids, "
    "panel genes and label rule ids. The tools listed are the audits a plan may schedule. The controls (the "
    "random-thinning control and the label-sensitivity check) are not plan steps: after each audit runs, an agent "
    "reads its result and decides which controls it needs. If the question needs an analysis no listed tool provides, "
    "plan what the tools can do and say what is left out in the summary. Split the question into sub_claims, one per "
    "testable part: each names a cell type label from the label rules, its panel genes, and what the researcher's "
    "hypothesis predicts under stricter assignment conditions: 'holds' (the signal is real cell content) or 'drops' "
    "(it is admixture from neighbouring cells). Record the researcher's prediction as the question states or implies "
    "it; never predict an outcome yourself. Respond with JSON that matches the response schema."
)

REPLAN_FEEDBACK = (
    "SpatialScout rejected that plan: {reason}\nPropose the plan again, using only the tools listed, with arguments "
    "valid for this dataset. This is the only re-plan allowed. Respond with only the JSON object."
)

AGENT_INSTRUCTIONS = (
    "You are SpatialScout's investigating agent. A researcher approved a plan, and its tools have run. You now read "
    "one observation (a tool's result) and decide which follow-up tools, if any, it calls for. Rules:\n"
    "- Every follow-up must cite the observation that prompted it (its observation_id) and give the reason, naming "
    "what in that observation you are responding to.\n"
    "- Only tools in the registry can run, with arguments valid against their arguments_schema. To test the same "
    "result, reuse the cited observation's arguments exactly.\n"
    "- Required controls. Verification fails any claim that does not cite each control required of it: a random-thinning "
    "control for any claim about assignment sensitivity, and a label-sensitivity check for any claim about a population "
    "whose label rule involves the claim's genes, or decides membership against those genes' home cell type (a rule that "
    "ignores a gene still competes with that gene's home type if it can assign the cell to it instead). Read the label "
    "rules and the result's home cell types to decide which controls apply. Nobody runs a control for you.\n"
    "- Each tool call spends one of the investigation's tool calls; the remaining budget is given. Do not repeat a "
    "call that has already run.\n"
    "- List as open questions what the evidence leaves unsettled that these tools cannot answer.\n"
    "Respond with JSON that matches the response schema."
)

CLAIM_INSTRUCTIONS = (
    "You write one claim about one finding for SpatialScout. Word it cautiously and scope it to the population: name "
    "its cell type label and its label rule, in the style of 'Co-expression persists under the tested restriction in "
    "cells labelled <cell type> by our <label rule> rule.' Never imply that the authors' labels are replicated, that a biological state is proven, or that a "
    "result is an artifact, robust, validated or significant. Use only numbers that appear in the finding or in its "
    "controls, and list every number the text uses in `cited`, with the field it comes from, written like "
    "sections[<section_id>].conditions[<condition>].<field>, pooled[<condition>].<field>, "
    "eligible_section_ids.count, or controls[<control_id>].<field> for a control. Write shares as percentages or "
    "fractions of the cited value. Respond with JSON that matches the response schema."
)

REDRAFT_FEEDBACK = (
    "SpatialScout cannot use that claim:\n- {problems}\nWrite it again so that every number in the text is a cited "
    "number whose source holds that value. This is the only redraft allowed. Respond with only the JSON object."
)


def dataset_context(dataset: DatasetManifest, label_rules: LabelRuleSet | None) -> dict[str, Any]:
    """What the planner needs to name valid arguments: section ids and groups, the panel and the label rules."""
    rules = (
        [{"label_rule_id": r.label_rule_id, "description": r.description, "ignored_genes": r.ignored_genes,
          "cell_types": sorted(r.markers)} for r in label_rules.rules]
        if label_rules
        else [{"label_rule_id": rule} for rule in dataset.label_rule_ids]
    )
    return {
        "dataset_id": dataset.dataset_id,
        "synthetic": dataset.synthetic,
        "sections": [
            {"section_id": s.section_id, "group": s.group, **({"duplicate_of": s.duplicate_of} if s.duplicate_of else {})}
            for s in dataset.sections
        ],
        "panel": dataset.panel,
        "label_rules": rules,
        "default_label_rule_id": label_rules.default_label_rule_id if label_rules else dataset.label_rule_ids[0],
    }


def _inputs(name: str, payload: Any) -> CacheInput:
    return CacheInput(name=name, version="json", sha256=sha256_hex(canonical_json(payload)))


def plan_request(
    question: str, report: CapabilityReport, tools: Sequence[ToolSpec], dataset: dict[str, Any]
) -> tuple[ModelRequest, list[CacheInput]]:
    payload = {
        "question": question,
        "dataset": dataset,
        "capability_report": report.model_dump(mode="json"),
        "tools": [t.model_dump(mode="json") for t in tools],
    }
    request = ModelRequest(
        provider="meta",
        model=PLANNER_MODEL,
        messages=[ChatMessage(role="system", content=PLANNER_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=PlanProposal.model_json_schema(),
    )
    inputs = [CacheInput(name="capability_report", version=report.schema_version, sha256=checksum(report)), _inputs("dataset", dataset)]
    inputs += [CacheInput(name=f"tool:{t.name}", version=t.version, sha256=checksum(t)) for t in tools]
    return request, inputs


def replan_request(request: ModelRequest, rejected: str, reason: str) -> ModelRequest:
    return request.model_copy(
        update={
            "messages": [
                *request.messages,
                ChatMessage(role="assistant", content=rejected[:20000]),
                ChatMessage(role="user", content=REPLAN_FEEDBACK.format(reason=reason)),
            ]
        }
    )


def observation_view(artifact: BaseModel) -> dict[str, Any]:
    """An artifact as the agent reads it: everything except the per-region and exploratory detail, and the per-section
    values only when there are few enough sections to read (the pooled values and verdicts carry the rest)."""
    dumped = artifact.model_dump(mode="json", exclude={"evidence_regions", "exploratory_sections", "rules", "marker_pairs"})
    if len(dumped.get("sections", [])) > 3:
        dumped.pop("sections")
        dumped["sections_omitted"] = "per-section values omitted; pooled values cover the eligible sections"
    return dumped


def follow_up_request(
    question: str,
    plan: Plan,
    observations: Sequence[dict[str, Any]],
    inspected: str,
    tools: Sequence[ToolSpec],
    tool_calls_used: int,
) -> tuple[ModelRequest, list[CacheInput]]:
    """Muse Spark 1.3 reads observation `inspected`, with every earlier observation for context."""
    payload = {
        "question": question,
        "plan": {"summary": plan.summary, "steps": [s.model_dump(mode="json") for s in plan.steps]},
        "tools": [t.model_dump(mode="json") for t in tools],
        "budget": {"max_tool_calls": plan.budget.max_tool_calls, "tool_calls_used": tool_calls_used,
                   "tool_calls_left": plan.budget.max_tool_calls - tool_calls_used},
        "observations": list(observations),
        "read_now": inspected,
    }
    request = ModelRequest(
        provider="meta",
        model=AGENT_MODEL,
        messages=[ChatMessage(role="system", content=AGENT_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=FollowUpDecision.model_json_schema(),
    )
    inputs = [_inputs("observations", list(observations))]
    inputs += [CacheInput(name=f"tool:{t.name}", version=t.version, sha256=checksum(t)) for t in tools]
    return request, inputs


def claim_request(
    question: str, finding: AuditResult, tool: ToolSpec, controls: Sequence[BaseModel] = ()
) -> tuple[ModelRequest, list[CacheInput]]:
    payload: dict[str, Any] = {
        "question": question,
        "finding": finding.model_dump(mode="json", exclude={"evidence_regions", "exploratory_sections"}),
    }
    if controls:
        payload["controls"] = [c.model_dump(mode="json", exclude={"sections"}) for c in controls]
    request = ModelRequest(
        provider="baseten",
        model=CLAIM_DRAFTING_MODEL,
        messages=[ChatMessage(role="system", content=CLAIM_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=ClaimDraft.model_json_schema(),
    )
    inputs = [CacheInput(name=f"artifact:{tool.name}", version=tool.version, sha256=checksum(finding))]
    inputs += [CacheInput(name=f"control:{getattr(c, 'control_id', '')}", version="json", sha256=checksum(c)) for c in controls]
    return request, inputs


def redraft_request(request: ModelRequest, rejected: str, problems: Sequence[str]) -> ModelRequest:
    return request.model_copy(
        update={
            "messages": [
                *request.messages,
                ChatMessage(role="assistant", content=rejected[:20000]),
                ChatMessage(role="user", content=REDRAFT_FEEDBACK.format(problems="\n- ".join(problems))),
            ]
        }
    )
