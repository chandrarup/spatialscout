"""The literature sub-agent's sources and its honesty gate.

Records come only from Europe PMC's REST search (https://europepmc.org/RestfulWebService), fetched live and stored
verbatim in the lab's recording, or replayed from it. Muse Spark summarises only those records; `gate` drops any
statement that cites a record that was not fetched, and `co_mention` counts in code how many fetched records mention
every term group, so the "is this reported?" line never rests on a model's memory."""

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

import httpx2 as httpx

from ..contracts import CoMention, LiteratureDigest, LiteratureRecord, LiteratureStatement

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PAGE_SIZE = 25
ABSTRACT_CHARS = 1500

# Gene and protein names, and cell-type words, as the literature writes them. Matching is case-insensitive, on word
# boundaries; a record "mentions" a group when it contains any of its terms.
GENE_TERMS: dict[str, list[str]] = {
    "LRP2": ["LRP2", "megalin", "gp330"],
    "CUBN": ["CUBN", "cubilin"],
    "UMOD": ["UMOD", "uromodulin", "Tamm-Horsfall"],
    "NPHS1": ["NPHS1", "nephrin"],
}
CELL_TERMS: dict[str, list[str]] = {
    "Podocyte": ["podocyte", "podocytes", "visceral epithelial"],
    "B cell": ["B cell", "B cells", "B-cell", "B-cells", "B lymphocyte", "B lymphocytes"],
    "PT": ["proximal tubule", "proximal tubular"],
    "TAL": ["thick ascending limb"],
}
HUMAN_TERMS = ["human", "patient", "patients", "biopsy", "biopsies"]


class LiteratureSource(Protocol):
    kind: str

    async def search(self, query: str) -> dict[str, Any]:
        """Europe PMC's JSON response for the query, as returned."""
        ...


class EuropePmcLive:
    kind = "live"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport
        self.fetched: dict[str, dict[str, Any]] = {}

    async def search(self, query: str) -> dict[str, Any]:
        params = {"query": query, "format": "json", "pageSize": str(PAGE_SIZE), "resultType": "core", "sort": "CITED desc"}
        async with httpx.AsyncClient(timeout=30, transport=self._transport) as client:
            response = await client.get(EUROPE_PMC, params=params)
            response.raise_for_status()
            data = response.json()
        self.fetched[query] = data
        return data


class RecordedLiterature:
    """Europe PMC responses stored by a live lab run, served by exact query."""

    kind = "replay"

    def __init__(self, responses: Mapping[str, dict[str, Any]]) -> None:
        self._responses = dict(responses)

    @classmethod
    def load(cls, path: Path) -> "RecordedLiterature":
        return cls(json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {})

    async def search(self, query: str) -> dict[str, Any]:
        if query not in self._responses:
            raise LookupError(f"no recorded Europe PMC response for the query {query!r}")
        return self._responses[query]


def records(data: Mapping[str, Any]) -> tuple[int, list[LiteratureRecord]]:
    """Europe PMC's hit count and its records, in the order it returned them."""
    out = []
    for r in data.get("resultList", {}).get("result", []):
        pmid = r.get("pmid")
        source, ident = r.get("source", "MED"), r.get("id", "")
        year = r.get("pubYear")
        out.append(
            LiteratureRecord(
                record_id=f"PMID:{pmid}" if pmid else f"{source}:{ident}",
                pmid=pmid,
                doi=r.get("doi"),
                title=re.sub(r"<[^>]+>", "", r.get("title", "")).strip(),
                journal=(r.get("journalInfo") or {}).get("journal", {}).get("title") or r.get("bookOrReportDetails", {}).get("publisher"),
                year=int(year) if year and str(year).isdigit() else None,
                first_author=(r.get("authorString") or "").split(",")[0].strip() or None,
                abstract=re.sub(r"<[^>]+>", "", r.get("abstractText", ""))[:ABSTRACT_CHARS],
                url=f"https://europepmc.org/article/{source}/{ident}",
            )
        )
    return int(data.get("hitCount", 0)), out


def gate(digest: LiteratureDigest, fetched: Sequence[LiteratureRecord]) -> tuple[list[LiteratureStatement], list[str]]:
    """Keep a statement only when it cites at least one record and every record it cites was fetched."""
    known = {r.record_id for r in fetched}
    kept, dropped = [], []
    for s in digest.statements:
        unknown = [c for c in s.cites if c not in known]
        if not s.cites:
            dropped.append(f"no citation: {s.text}")
        elif unknown:
            dropped.append(f"cites records that were not fetched ({', '.join(unknown)}): {s.text}")
        else:
            kept.append(LiteratureStatement(text=s.text, cites=list(dict.fromkeys(s.cites))))
    return kept, dropped


def _mentions(text: str, terms: Sequence[str]) -> bool:
    return any(re.search(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE) for t in terms)


def co_mention(fetched: Sequence[LiteratureRecord], term_groups: Sequence[Sequence[str]]) -> CoMention:
    hits = [r.record_id for r in fetched if all(_mentions(f"{r.title} {r.abstract}", group) for group in term_groups)]
    return CoMention(term_groups=[list(g) for g in term_groups], records_searched=len(fetched), records_mentioning_all=len(hits), record_ids=hits)


def term_groups(cell_type: str, genes: Sequence[str]) -> list[list[str]]:
    groups = [GENE_TERMS.get(g, [g]) for g in genes[:1]]
    groups.append(CELL_TERMS.get(cell_type, [cell_type]))
    groups.append(HUMAN_TERMS)
    return groups


def co_mention_note(count: CoMention, query: str, hit_count: int) -> str:
    gene, cell, _ = count.term_groups
    return (
        f"{count.records_mentioning_all} of the {count.records_searched} most-cited records read (of {hit_count:,} Europe PMC hits for "
        f"'{query}') mention {gene[0]} together with {cell[0]}s in a human context in their title or abstract. "
        "A count over the records read, not a search of everything published."
    )
