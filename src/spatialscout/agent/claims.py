"""The claim-drafting gate: a draft is checked before it becomes a claim.

A draft passes when:
- it cites at least one number, and every cited source resolves to that value in the finding or one of its controls;
- every number its text writes is one of the cited numbers (as written, or as a percentage of a share);
- it names the population's cell type, and none of the wording the glossary rules out.

This is a gate on the model's output, not verification: ticket 10 recomputes every cited number independently.
"""

import re
from collections.abc import Mapping

from pydantic import BaseModel

from ..contracts import AuditResult, ClaimDraft
from ..verify.citations import UnresolvedSource, resolve_source, same_number

# Wording the glossary rules out of claims: verdicts on biological truth, and admixture as contamination or leakage.
FORBIDDEN_WORDS = (
    "artifact", "artefact", "robust", "robustly", "validated", "validates", "proves", "proven", "proof", "confirms",
    "confirmed", "significant", "significantly", "contamination", "contaminated", "leakage", "leaked", "fake",
    "false positive", "real biology", "truly",
)

# A number written on its own: not part of an identifier (LRP2, GSM8720409, nphs1-anchored-v1), and not a distance
# cap's micrometres (1 µm, 2 um), which name a condition rather than cite a value.
_NUMBER = re.compile(r"(?<![A-Za-z0-9_.\-])(\d+(?:\.\d+)?)(\s*%)?(?![A-Za-z0-9_]|\.\d|\s*[µμu]m\b)")


def claim_problems(draft: ClaimDraft, finding: AuditResult, controls: Mapping[str, BaseModel]) -> list[str]:
    """Every reason the draft cannot become a claim; empty when it passes."""
    problems = []
    if not draft.cited:
        problems.append("the claim cites no number")
    for name, number in draft.cited.items():
        try:
            actual = resolve_source(number.source, finding, controls)
        except UnresolvedSource as error:
            problems.append(f"cited {name}: {error}")
            continue
        if not same_number(number.value, actual):
            problems.append(f"cited {name} is {number.value}, but {number.source} is {actual}")
    values = [n.value for n in draft.cited.values() if isinstance(n.value, int | float)]
    for match in _NUMBER.finditer(draft.text):
        written, percent = match.group(1), bool(match.group(2))
        if not any(_writes(written, percent, value) for value in values):
            problems.append(f"the text writes {match.group(0).strip()}, which is none of the cited numbers")
    lowered = draft.text.lower()
    if finding.population.cell_type.lower() not in lowered:
        problems.append(f"the text does not name the population it is about ({finding.population.cell_type})")
    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            problems.append(f"the text uses {word!r}, which a claim must not (it states no verdict on biological truth)")
    return problems


def _writes(written: str, percent: bool, value: float | int) -> bool:
    """Whether the text's number is this cited value as written: itself, or a share written as a percentage, each
    to the precision the text uses."""
    decimals = len(written.split(".")[1]) if "." in written else 0
    tolerance = 0.5 * 10**-decimals + 1e-9
    number = float(written)
    candidates = [value * 100] if percent else [value, value * 100]
    return any(abs(number - candidate) <= tolerance for candidate in candidates)
