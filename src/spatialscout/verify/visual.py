"""The visual check: Muse Spark 1.3 reads a claim's composite figure and answers three questions against a schema.

1. Does Panel A's direction match the direction the claim states?
2. Does a single section drive Panel A?
3. Does Panel B show the neighbour pattern the claim states? Asked only when the claim states one, and backed by the
   computed neighbour-proximity shares, so the image never answers it by construction.

The request carries the claim's subject and its stated direction and pattern, not its full text, so variants that
change only a cited number share one model call. A visual check is a consistency check, not ground truth: a
disagreement disputes the claim, it never fails it. A response that cannot be had (no stored response, a provider
error, an unusable answer) leaves the check unavailable.
"""

import hashlib
from typing import Any

from ..contracts import (
    AuditResult,
    CacheInput,
    ChatMessage,
    CheckResult,
    Claim,
    CompositeFigure,
    ModelRequest,
    VisualAnswer,
    canonical_json,
    sha256_hex,
)
from ..gateway import GatewayError, ModelGateway
from .checks import evidence_section, stated_direction

VISUAL_MODEL = "muse-spark-1.3"
VISUAL_CHECK_VERSION = "visual-1"

VISUAL_INSTRUCTIONS = (
    "You check one claim against its composite figure for SpatialScout. Panel A plots, per assignment condition, each "
    "section's observed value (thin grey lines), the pooled observed value (black), the home-matched and cell-matched "
    "random-thinning expectations, and a threshold line (home-matched x 2^-0.5). Panel B is a tissue crop: population "
    "nuclei, home-type nuclei, retained molecules (blue) and molecules excluded under the stricter condition (yellow). "
    "Read the figure itself; do not assume the claim is right. Answer:\n"
    "- panel_a_direction: holds if the pooled observed line stays at or above the threshold line under every stricter "
    "condition, drops if it falls below it under at least one, unclear if you cannot tell;\n"
    "- panel_a_matches_claim: whether that is the direction the claim states;\n"
    "- single_section_drives_panel_a: whether one section's line alone accounts for the pooled direction;\n"
    "- panel_b_matches_claim: whether Panel B, read together with the computed neighbour-proximity shares given, shows "
    "the neighbour pattern the claim states; null when the claim states none.\n"
    "Also check that the figure's title names the claim's population and genes; if it does not, the claim does not "
    "match the figure. Respond with JSON that matches the response schema."
)

DIRECTION_TEXT = {
    "holds": "the pooled observed value holds at or above the home-matched expectation x 2^-0.5 under every stricter condition",
    "drops": "the pooled observed value drops below the home-matched expectation x 2^-0.5 under at least one stricter condition",
}
PATTERN_TEXT = {
    "excluded_nearer_home": "in Panel B's section, excluded molecules lie closer to a cell of their gene's home type more often "
    "than retained molecules do",
    "excluded_not_nearer_home": "in Panel B's section, excluded molecules lie closer to a cell of their gene's home type no more "
    "often than retained molecules do",
}


def visual_request(claim: Claim, finding: AuditResult, figure: CompositeFigure) -> tuple[ModelRequest, list[CacheInput]]:
    """The visual-check request: the claim's subject, stated direction and pattern, and the computed shares."""
    direction = stated_direction(claim)
    payload: dict[str, Any] = {
        "claim_subject": {
            "cell_type": finding.population.cell_type,
            "label_rule_id": finding.population.label_rule_id,
            "genes": finding.genes,
            "measure": finding.measure,
        },
        "claim_states_direction": DIRECTION_TEXT[direction] if direction else None,
        "claim_states_neighbour_pattern": PATTERN_TEXT[claim.neighbour_pattern] if claim.neighbour_pattern else None,
        "figure_title_panels": {"panel_a": figure.panel_a, "panel_b": figure.panel_b},
    }
    if direction is None:
        payload["claim_text"] = claim.text
    if claim.neighbour_pattern:
        payload["computed_neighbour_proximity_shares"] = _shares(finding)
    request = ModelRequest(
        provider="meta",
        model=VISUAL_MODEL,
        messages=[ChatMessage(role="system", content=VISUAL_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=VisualAnswer.model_json_schema(),
    )
    inputs = [CacheInput(name="visual_check", version=VISUAL_CHECK_VERSION, sha256=sha256_hex(canonical_json(payload)))]
    return request, inputs


def _shares(finding: AuditResult) -> dict[str, Any] | None:
    where = evidence_section(finding)
    if where is None:
        return None
    section = next((s for s in finding.sections if s.section_id == where[0]), None)
    row = next((c for c in (section.conditions if section else []) if c.condition.value == where[1]), None)
    if row is None:
        return None
    return {
        "section_id": where[0],
        "condition": where[1],
        "excluded": row.neighbour_proximity_share_excluded,
        "retained": row.neighbour_proximity_share_retained,
        "meaning": "share of the result's molecules strictly closer to a cell of their gene's home type than to their own cell's centroid",
    }


async def visual_check(
    gateway: ModelGateway | None, claim: Claim, finding: AuditResult | None, figure: CompositeFigure | None, png: bytes | None,
    memo: dict[str, Any] | None = None,
) -> tuple[CheckResult, VisualAnswer | None]:
    if gateway is None:
        return _unavailable("no model gateway: the visual check needs Muse Spark 1.3 or its stored response"), None
    if finding is None or figure is None or png is None:
        return _unavailable("no composite figure to read"), None
    request, inputs = visual_request(claim, finding, figure)
    key = sha256_hex(canonical_json({"request": request.model_dump(mode="json"), "png": hashlib.sha256(png).hexdigest()}))
    if memo is not None and key in memo:
        answer = memo[key]
    else:
        try:
            answer, _ = await gateway.complete_json("visual_check", request, inputs, VisualAnswer, image=png)
        except GatewayError as error:
            return _unavailable(f"the visual check could not be run: {error}"), None
        if memo is not None:
            memo[key] = answer
    reasons = []
    if not answer.panel_a_matches_claim:
        reasons.append(f"visual check: Panel A reads as '{answer.panel_a_direction}', which does not match the claim's direction")
    if answer.single_section_drives_panel_a:
        reasons.append("visual check: a single section drives Panel A")
    if claim.neighbour_pattern is not None and answer.panel_b_matches_claim is False:
        reasons.append("visual check: Panel B does not show the neighbour pattern the claim states")
    if reasons:
        return CheckResult(kind="visual", status="disputed", details=f"{reasons[0]}. {answer.explanation}", reasons=reasons), answer
    return CheckResult(kind="visual", status="passed", details=answer.explanation), answer


def _unavailable(reason: str) -> CheckResult:
    return CheckResult(kind="visual", status="unavailable", details=reason, reasons=[reason])
