"""Contracts for the data check: before a question runs, what it needs (genes, cell types, disease groups, organ,
species, assay) set against what the workspace holds, and where to get what it lacks: the researcher's own sections,
or public datasets found by a live repository search. Every match and gap is computed in code from the question's
text and the workspace's artifacts; every dataset is a record the repository returned. No model is involved."""

from typing import Literal

from pydantic import Field

from .base import Contract

NeedKind = Literal["gene", "cell_type", "group", "organ", "species", "assay"]


class NeedMatch(Contract):
    """One thing the question names, and whether the workspace holds it."""

    kind: NeedKind
    text: str = Field(description="As written in the question.")
    value: str = Field(description="What it was read as: an HGNC symbol, a cell-type label, a disease group, an organ, a species or an assay.")
    available: bool
    note: str = ""


class DataGap(Contract):
    kind: NeedKind
    item: str
    why: str
    hard: bool = Field(description="True when no run on this workspace can answer it (a gene off the panel, another organ, species "
                                   "or assay); false when a run would answer a nearby question instead.")


class PublicDataset(Contract):
    """One repository record, as returned. `technology` and `matches` are read from its title and summary by code."""

    accession: str
    title: str
    summary: str
    samples: int | None = None
    published: str | None = None
    technology: str
    auditable_here: bool = Field(description="Human Xenium output (GEO's taxon), which the Your data page audits as uploaded.")
    matches: list[str] = Field(description="Which of the question's needs the title or summary names.")
    url: str


class UploadPrefill(Contract):
    cell_type: str | None = None
    genes: list[str] = Field(default_factory=list)


class DataFit(Contract):
    question: str
    dataset_id: str
    answerable: bool = Field(description="No hard gap: a run on this workspace can address the question.")
    matched: list[NeedMatch]
    gaps: list[DataGap]
    have: str = Field(description="One sentence: what the workspace holds.")
    upload_needs: list[str] = Field(description="What the researcher's own sections must contain for this question.")
    upload_prefill: UploadPrefill
    related_recordings: list[str] = Field(description="Recorded questions on the same genes or cell types.")
    search_query: str
    search_url: str
    datasets: list[PublicDataset]
    search_note: str = Field(description="Which query returned the datasets, or why the search could not run.")
