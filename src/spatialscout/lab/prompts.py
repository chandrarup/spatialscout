"""The lab's model requests, built deterministically from their inputs so a recorded lab replays by cache key.

- dispatch: Muse Wonder reads the verdict, the verified claims and the sub-agent registry, and chooses sub-agents;
- literature: Muse Spark 1.3 reads only the records Europe PMC returned and writes cited statements about them.
"""

from collections.abc import Sequence
from typing import Any

from ..contracts import (
    CacheInput,
    ChatMessage,
    DispatchProposal,
    LiteratureDigest,
    LiteratureRecord,
    ModelRequest,
    canonical_json,
    sha256_hex,
)

DISPATCH_MODEL = "muse-wonder-1.0"
READER_MODEL = "muse-spark-1.3"
MAX_TOKENS = 6000

REGISTRY: list[dict[str, str]] = [
    {
        "agent": "literature",
        "does": "Searches Europe PMC with one boolean query you write, reads the 25 most-cited records, and reports what they say about the sub-claim's gene in its cell type, citing only those records.",
        "when": "Whenever it helps to know whether the sub-claim's result is already reported, contradicted or untested in the literature.",
    },
    {
        "agent": "protein_crosscheck",
        "does": "Runs the protein-level audit on two KPMP CODEX kidney biopsies (a healthy reference and a diseased participant): the share of marker-positive cells as each cell's outline is trimmed. A different assay and different people: a second line of evidence, not a replication.",
        "when": "Only for sub-claims about LRP2 in podocytes (protein: LRP2 in Podocalyxin+ cells) or UMOD in B cells (UMOD in CD20+ cells).",
    },
    {
        "agent": "publication_figure",
        "does": "Renders the sub-claim's audit result as a two-panel vector figure at journal width, with a legend written from the computed numbers.",
        "when": "For every sub-claim that rests on a verified claim.",
    },
]

DISPATCH_INSTRUCTIONS = """You run the follow-up lab of a spatial-transcriptomics agent. An investigation has finished: you get the question,
the verdict on each sub-claim (index from 0), the verified claims with their computed numbers, and a registry of
sub-agents. Choose the sub-agents to start; they run at the same time.

Rules:
- Use only agents from the registry, and only as its 'when' says.
- At most 8 tasks. One task per agent per sub-claim.
- Every task has a `query` field. For a literature task it is required and must not be empty: write it in Europe PMC
  boolean syntax. For other agents set it to "". Name the gene with its protein name (for example
  '(LRP2 OR megalin)'), the cell type, and restrict to human ('AND human'). Keep it short enough to return records.
- `reason` is one plain sentence a scientist would accept.
- Do not invent results; the sub-agents compute and fetch them.
Respond with JSON matching the schema, and nothing else."""

LITERATURE_INSTRUCTIONS = """You read literature records for a scientist. You get one sub-claim, the computed result it rests on, and the
records Europe PMC returned for a query (id, title, year, journal, abstract). Write what these records report that
bears on the sub-claim.

Rules:
- Use only these records. Never use anything you remember from elsewhere.
- Each statement is one sentence and cites the record_id values it rests on (at least one). Cite only ids listed.
- Report what a record states, with its species or system when the abstract gives it (human, rat, mouse, cell line).
- Do not say anything is new, novel or first. If the records do not address the sub-claim in human tissue, say so in `gap`.
- At most 6 statements.
Respond with JSON matching the schema, and nothing else."""


def _inputs(name: str, payload: Any) -> CacheInput:
    return CacheInput(name=name, version="json", sha256=sha256_hex(canonical_json(payload)))


def dispatch_request(question: str, verdicts: Sequence[dict[str, Any]], claims: Sequence[dict[str, Any]]) -> tuple[ModelRequest, list[CacheInput]]:
    payload = {"question": question, "verdicts": list(verdicts), "verified_claims": list(claims), "registry": REGISTRY}
    request = ModelRequest(
        provider="meta",
        model=DISPATCH_MODEL,
        messages=[ChatMessage(role="system", content=DISPATCH_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=DispatchProposal.model_json_schema(),
        max_tokens=MAX_TOKENS,
    )
    return request, [_inputs("lab_dispatch", payload)]


def literature_request(sub_claim: dict[str, Any], result: dict[str, Any], query: str, fetched: Sequence[LiteratureRecord]) -> tuple[ModelRequest, list[CacheInput]]:
    payload = {
        "sub_claim": sub_claim,
        "computed_result": result,
        "query": query,
        "records": [r.model_dump(mode="json", include={"record_id", "title", "year", "journal", "abstract"}) for r in fetched],
    }
    request = ModelRequest(
        provider="meta",
        model=READER_MODEL,
        messages=[ChatMessage(role="system", content=LITERATURE_INSTRUCTIONS), ChatMessage(role="user", content=canonical_json(payload))],
        response_schema=LiteratureDigest.model_json_schema(),
        max_tokens=MAX_TOKENS,
    )
    return request, [_inputs("literature_records", payload)]
