"""The data check: read what a question needs, set it against what the workspace holds, and say where to get the rest.

Reading is deterministic, no model:
- genes: words that are HGNC protein-coding symbols or unambiguous aliases (`artifacts/reference/hgnc_genes.tsv.gz`),
  plus protein names (megalin, uromodulin, ...). A word with a digit matches in any case ("nphs1"); a word of letters
  only must be written in capitals ("UMOD"), so English words are never read as genes. Disease, cell-type and assay
  abbreviations (AKI, PT, TAL, ATAC, ...) are never genes.
- cell types, disease groups, organs, species and assays: from fixed phrase lists, set against the labels and groups
  in the dataset's own artifacts.

The public datasets come from a live search of NCBI GEO (E-utilities), built from the needs; each is a record GEO
returned, with its technology read from its title and summary.
"""

import asyncio
import gzip
import re
from collections.abc import Awaitable, Callable, Sequence
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from ..contracts import DataFit, DataGap, NeedMatch, PublicDataset, UploadPrefill

PROTEIN_NAMES = {
    "megalin": "LRP2", "cubilin": "CUBN", "uromodulin": "UMOD", "tamm-horsfall": "UMOD", "nephrin": "NPHS1",
    "podocin": "NPHS2", "podocalyxin": "PODXL", "synaptopodin": "SYNPO", "aquaporin-2": "AQP2", "aquaporin 2": "AQP2",
    "collagen i": "COL1A1", "fibronectin": "FN1", "periostin": "POSTN", "vimentin": "VIM", "kim-1": "HAVCR1",
    "ngal": "LCN2", "renin": "REN", "apol1": "APOL1", "wt1": "WT1", "smooth muscle actin": "ACTA2", "asma": "ACTA2",
}
NOT_GENES = {
    # disease groups and clinical terms
    "AKI", "CKD", "DKD", "IGAN", "MCD", "MN", "FSGS", "LN", "SLE", "ANCA", "ADPKD", "ESRD", "ESKD", "GFR", "EGFR", "UACR",
    "IGA", "COVID", "RCC", "HIV", "APOL", "TMA", "AAV",
    # cell-type abbreviations used in kidney atlases
    "PT", "TAL", "DCT", "CNT", "PC", "IC", "PEC", "EC", "VSMC", "MD", "JG", "NK", "DC", "TREG", "POD",
    # assays and methods
    "RNA", "DNA", "MRNA", "ATAC", "UMAP", "TSNE", "PCA", "QC", "ROI", "FOV", "SAM", "CODEX", "SNRNA", "SCRNA", "ISH",
    "FISH", "IHC", "IF", "H", "E", "HE", "PAS", "KPMP", "GEO", "GSE", "NCBI", "ML", "AI", "OK", "VS", "OR", "AND", "NOT",
    "I", "A", "T", "B", "X", "Y", "UK", "US", "USA", "LLM",
}
CELL_TYPES: dict[str, tuple[str, ...]] = {
    "Podocyte": ("podocyte",),
    "PEC": ("parietal epithelial", "parietal cell", "pec"),
    "PT": ("proximal tubule", "proximal tubular", "proximal convoluted", "pt cell"),
    "TAL": ("thick ascending limb", "loop of henle", "tal cell"),
    "DCT": ("distal convoluted", "distal tubule", "dct cell"),
    "PC": ("principal cell",),
    "IC": ("intercalated",),
    "Endothelial": ("endothelial", "endothelium"),
    "Mesangial/Pericyte": ("mesangial", "pericyte"),
    "Fibroblast": ("fibroblast", "myofibroblast", "stromal cell"),
    "T cell": ("t cell", "t-cell", "t lymphocyte", "cd4+", "cd8+", "regulatory t", "treg"),
    "B cell": ("b cell", "b-cell", "b lymphocyte"),
    "Myeloid": ("myeloid", "macrophage", "monocyte", "dendritic cell"),
}
UNLABELLED_CELLS = (
    "plasma cell", "nk cell", "natural killer", "neutrophil", "mast cell", "eosinophil", "macula densa", "juxtaglomerular",
    "connecting tubule", "thin limb", "collecting duct", "smooth muscle", "adipocyte", "tumor cell", "tumour cell",
    "cancer cell", "stem cell", "progenitor", "renin cell", "platelet", "erythrocyte", "red blood cell",
)
GROUPS: dict[str, tuple[str, ...]] = {
    "Control": ("healthy", "control", "normal kidney", "reference tissue"),
    "DKD": ("diabetic", "diabetes", "dkd", "diabetic nephropathy"),
    "IgAN": ("iga nephropathy", "igan", "iga"),
    "MCD": ("minimal change", "mcd"),
    "MN": ("membranous", " mn "),
}
OTHER_DISEASES: dict[str, tuple[str, ...]] = {
    "AKI": ("acute kidney injury", "aki"),
    "CKD": ("chronic kidney disease", "ckd"),
    "FSGS": ("fsgs", "focal segmental"),
    "Lupus nephritis": ("lupus", "sle"),
    "ANCA vasculitis": ("anca", "vasculitis"),
    "Transplant rejection": ("transplant", "allograft", "rejection"),
    "Polycystic kidney disease": ("polycystic", "adpkd", "pkd"),
    "Alport syndrome": ("alport",),
    "Hypertensive nephrosclerosis": ("hypertensive", "hypertension", "nephrosclerosis"),
    "C3 glomerulopathy": ("c3 glomerulopathy", "c3g"),
    "Amyloidosis": ("amyloid",),
    "Renal cell carcinoma": ("carcinoma", "rcc", "kidney cancer", "renal cancer", "tumour", "tumor"),
    "COVID-19": ("covid", "sars-cov-2"),
}
ORGANS: dict[str, tuple[str, ...]] = {
    "liver": ("liver", "hepatic", "hepatocyte"), "lung": ("lung", "pulmonary", "alveolar"), "brain": ("brain", "neuron", "cortex of the brain", "hippocampus"),
    "heart": ("heart", "cardiac", "cardiomyocyte"), "intestine": ("intestine", "colon", "gut", "intestinal"), "breast": ("breast",),
    "pancreas": ("pancreas", "islet"), "skin": ("skin", "dermis", "keratinocyte"), "lymph node": ("lymph node", "tonsil"),
    "spleen": ("spleen",), "prostate": ("prostate",), "blood": ("pbmc", "peripheral blood"), "retina": ("retina",),
}
SPECIES: dict[str, tuple[str, ...]] = {
    "mouse": ("mouse", "mice", "murine"), "rat": ("rat ", "rats", "rat,"), "zebrafish": ("zebrafish",),
    "pig": ("porcine", "pig "), "non-human primate": ("macaque", "monkey", "primate"),
}
SPECIES_ORGANISM = {"mouse": "Mus musculus", "rat": "Rattus norvegicus", "zebrafish": "Danio rerio", "pig": "Sus scrofa", "non-human primate": "Macaca mulatta"}
ASSAYS: dict[str, tuple[tuple[str, ...], bool, str]] = {
    "chromatin accessibility": (("atac", "chromatin", "accessibility"), True, "The workspace holds RNA molecules and protein images, not chromatin."),
    "DNA methylation": (("methylation",), True, "No methylation data in the workspace."),
    "metabolites": (("metabolite", "metabolomic", "lipidomic"), True, "No metabolite data in the workspace."),
    "genome-wide expression": (("whole transcriptome", "genome-wide", "all genes", "whole-transcriptome"), True, "GSE286184 measured a 50-gene panel."),
    "clinical outcome": (("outcome", "survival", "progression", "egfr decline", "prognos", "mortality"), False,
                         "The workspace holds no clinical follow-up: a run reports tissue measurements only."),
    "treatment response": (("treatment", "drug", "therapy", "responder"), False, "No treatment records: a run reports tissue measurements only."),
    "time course": (("longitudinal", "over time", "time course", "time-course"), False, "Each biopsy is one time point."),
    "protein": (("protein", "antibody", "immunofluorescence"), False,
                "Protein is measured on the KPMP CODEX biopsies only, for the markers in their panel."),
}
KPMP_PROTEIN_GENES = {"PODXL": "Podocalyxin", "LRP2": "LRP2", "UMOD": "UMOD", "MS4A1": "CD20", "CD3E": "CD3", "CD8A": "CD8", "PTPRC": "CD45", "ACTA2": "aSMA", "PECAM1": "CD31"}
TECHNOLOGIES = (
    ("Xenium", r"xenium"), ("CosMx", r"cosmx|\bsmi\b"), ("MERFISH", r"merfish|merscope"), ("Visium", r"visium"),
    ("CODEX/PhenoCycler", r"codex|phenocycler"), ("Slide-seq", r"slide-?seq"), ("Stereo-seq", r"stereo-?seq"),
    ("Spatial (other)", r"spatial"), ("Single-cell", r"single[- ]cell|single[- ]nucle|scrna|snrna"),
)
GEO_TECH_TERMS = '(Xenium OR CosMx OR MERFISH OR Visium OR "spatial transcriptomics" OR "spatial transcriptomic" OR CODEX OR PhenoCycler)'

MIN_DATASETS = 4  # fewer from the full query: top up from the broader ones, in order

Searcher = Callable[[str], Awaitable[list[dict]]]


@lru_cache(maxsize=1)
def gene_vocabulary(path: Path) -> dict[str, str]:
    """Upper-case name -> approved HGNC symbol (symbols, then unambiguous aliases and previous symbols)."""
    names: dict[str, str] = {}
    aliases: dict[str, str] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            symbol, _, rest = line.rstrip("\n").partition("\t")
            names[symbol.upper()] = symbol
            for alias in filter(None, rest.split("|")):
                aliases.setdefault(alias, symbol)
    return {**aliases, **names}


def _phrases(text: str, table: dict[str, tuple[str, ...]]) -> list[tuple[str, str]]:
    found = []
    for value, phrases in table.items():
        for phrase in phrases:
            if phrase.strip() and re.search(rf"(?<![a-z0-9]){re.escape(phrase.strip())}(?:s|es)?(?![a-z0-9])", text):
                found.append((phrase.strip(), value))
                break
    return found


def read_needs(question: str, vocabulary: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    """(as written, read as) per kind of need. Pure: the same question always gives the same needs."""
    lower = f" {question.lower()} "
    genes: dict[str, str] = {}
    for name, symbol in PROTEIN_NAMES.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", lower):
            genes.setdefault(symbol, name)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]*[A-Za-z0-9]|[A-Za-z]", question)
    words = [t for t in tokens if t.isalpha() and len(t) > 1 and t.upper() not in NOT_GENES and vocabulary.get(t.upper()) != t.upper()]
    shouting = len(words) >= 4 and sum(t.isupper() for t in words) > len(words) / 2  # capitals no longer mark a gene
    for index, token in enumerate(tokens):
        upper = token.upper().rstrip("+")
        if upper in NOT_GENES or len(upper) < 2:
            continue
        lettered = not any(ch.isdigit() for ch in token)
        if lettered and (token != token.upper() or shouting):
            continue
        neighbours = tokens[max(0, index - 1):index] + tokens[index + 1:index + 2]
        if lettered and neighbours and all(n.isupper() and n.isalpha() and vocabulary.get(n) != n for n in neighbours):
            continue  # a capitalised phrase ("IS THE SET OK"), not a gene list
        symbol = vocabulary.get(upper)
        if symbol:
            genes.setdefault(symbol, token)
        elif re.fullmatch(r"[A-Z]{2,}[0-9]+[A-Z0-9]*", token) and not upper.startswith(("GSE", "GSM", "GPL", "PMID", "COVID")):
            genes.setdefault(token, token)  # gene-shaped (IGHG1, a non-coding gene): read as named, never mapped
    cells = _phrases(lower, CELL_TYPES)
    unlabelled = [(p, p) for p in UNLABELLED_CELLS if re.search(rf"(?<![a-z]){re.escape(p)}s?(?![a-z])", lower)]
    groups = _phrases(lower, GROUPS)
    diseases = _phrases(lower, OTHER_DISEASES)
    organs = _phrases(lower, ORGANS)
    species = _phrases(lower, SPECIES)
    assays = [(next(p for p in phrases if p in lower), name) for name, (phrases, _, _) in ASSAYS.items() if any(p in lower for p in phrases)]
    return {
        "genes": [(written, symbol) for symbol, written in genes.items()],
        "cells": cells, "unlabelled": unlabelled, "groups": groups, "diseases": diseases,
        "organs": organs, "species": species, "assays": assays,
    }


def check(
    question: str,
    *,
    vocabulary: dict[str, str],
    dataset_id: str,
    panel: Sequence[str],
    cell_types: Sequence[str],
    groups: dict[str, int],
    kpmp_categories: dict[str, int],
    recorded_questions: Sequence[str],
) -> DataFit:
    """Everything but the repository search. `groups`: disease group -> sections; `kpmp_categories`: KPMP enrollment
    category -> biopsies."""
    needs = read_needs(question, vocabulary)
    panel_set = set(panel)
    matched: list[NeedMatch] = []
    gaps: list[DataGap] = []

    for written, symbol in needs["genes"]:
        if symbol in panel_set:
            matched.append(NeedMatch(kind="gene", text=written, value=symbol, available=True, note=f"In the {dataset_id} panel."))
            continue
        protein = KPMP_PROTEIN_GENES.get(symbol)
        note = f" Its protein ({protein}) is imaged on the KPMP CODEX biopsies." if protein else ""
        matched.append(NeedMatch(kind="gene", text=written, value=symbol, available=False, note=f"Not in the {len(panel)}-gene {dataset_id} panel.{note}"))
        gaps.append(DataGap(kind="gene", item=symbol, hard=True, why=f"{symbol} is not among the {len(panel)} genes {dataset_id} measured, so no count of it exists here.{note}"))
    for written, label in needs["cells"]:
        ok = label in cell_types
        matched.append(NeedMatch(kind="cell_type", text=written, value=label, available=ok,
                                 note="" if written.lower() == label.lower() else f"Read as the '{label}' label."))
    for written, _ in needs["unlabelled"]:
        matched.append(NeedMatch(kind="cell_type", text=written, value=written, available=False, note="No label rule names this cell type."))
        gaps.append(DataGap(kind="cell_type", item=written, hard=True,
                            why=f"The label rules name {len(cell_types)} cell types ({', '.join(cell_types)}); {written}s are not one of them."))
    for written, group in needs["groups"]:
        n = groups.get(group, 0)
        matched.append(NeedMatch(kind="group", text=written, value=group, available=n > 0, note=f"{n} sections." if n else ""))
    for written, disease in needs["diseases"]:
        kpmp = kpmp_categories.get(disease, 0)
        extra = f" KPMP holds {kpmp} {disease} biopsy imaged for protein (CODEX)." if kpmp else ""
        matched.append(NeedMatch(kind="group", text=written, value=disease, available=False, note=f"Not a {dataset_id} group.{extra}"))
        gaps.append(DataGap(kind="group", item=disease, hard=False,
                            why=f"{dataset_id} holds {', '.join(f'{g} ({n})' for g, n in groups.items())}, no {disease}. A run would answer across these groups instead.{extra}"))
    for written, organ in needs["organs"]:
        matched.append(NeedMatch(kind="organ", text=written, value=organ, available=False))
        gaps.append(DataGap(kind="organ", item=organ, hard=True, why=f"Everything here is human kidney; nothing measures the {organ}."))
    for written, species in needs["species"]:
        matched.append(NeedMatch(kind="species", text=written, value=species, available=False))
        gaps.append(DataGap(kind="species", item=species, hard=True, why=f"Every biopsy here is human; none is {species}."))
    for written, assay in needs["assays"]:
        _, hard, why = ASSAYS[assay]
        matched.append(NeedMatch(kind="assay", text=written, value=assay, available=not hard, note=why))
        if hard or assay != "protein":
            gaps.append(DataGap(kind="assay", item=assay, hard=hard, why=why))

    gene_symbols = [m.value for m in matched if m.kind == "gene"]
    cell = next((m.value for m in matched if m.kind == "cell_type" and m.available), None)
    words = {w.lower() for w in gene_symbols} | {m.text.lower() for m in matched if m.kind == "cell_type"} | {m.value.lower() for m in matched if m.kind == "cell_type"}
    related = [q for q in recorded_questions if any(re.search(rf"(?<![a-z0-9]){re.escape(w)}", q.lower()) for w in words if len(w) > 1)]

    upload_needs = [
        "Xenium output per section: transcripts (transcript_id, feature_name, x_location, y_location, qv, cell_id, overlaps_nucleus, nucleus_distance) and cells (cell_id, x_centroid, y_centroid, cell_area, nucleus_area).",
        "At least three sections, so the result is a verdict and not one section's reading.",
    ]
    if gene_symbols:
        upload_needs.append(f"A panel that measures {', '.join(gene_symbols)}.")
    if cell:
        upload_needs.append(f"Cells are labelled with the frozen {dataset_id} rules, so the panel also needs the {cell} marker genes.")
    if any(g.kind == "species" for g in gaps):
        upload_needs.append("Human tissue: the label rules and gene scales are human.")

    query, url = geo_query(needs)
    hard = any(g.hard for g in gaps)
    return DataFit(
        question=question, dataset_id=dataset_id, answerable=not hard, matched=matched, gaps=gaps,
        have=(f"{dataset_id}: {sum(groups.values())} human kidney Xenium sections ({', '.join(f'{g} {n}' for g, n in groups.items())}), "
              f"a {len(panel)}-gene panel and {len(cell_types)} labelled cell types; plus {sum(kpmp_categories.values())} KPMP CODEX protein biopsies "
              f"({', '.join(f'{c} {n}' for c, n in kpmp_categories.items())})."),
        upload_needs=upload_needs,
        upload_prefill=UploadPrefill(cell_type=cell, genes=gene_symbols),
        related_recordings=related, search_query=query, search_url=url, datasets=[], search_note="",
    )


def _or(terms: Sequence[str]) -> str:
    quoted = [f'"{t}"' if " " in t else t for t in terms]
    return quoted[0] if len(quoted) == 1 else "(" + " OR ".join(quoted) + ")"


def geo_queries(needs: dict[str, list[tuple[str, str]]]) -> list[str]:
    """From most to least specific; the search takes the first that returns records."""
    species = [v for _, v in needs["species"]]
    organism = f'"{SPECIES_ORGANISM[species[0]]}"[Organism]' if species else '"Homo sapiens"[Organism]'
    organs = [v for _, v in needs["organs"]] or ["kidney", "renal"]
    base = f"{_or(organs)} AND {GEO_TECH_TERMS} AND {organism} AND gse[Entry Type]"
    disease = [v for _, v in needs["diseases"]] + [v for _, v in needs["groups"] if v != "Control"]
    genes = [v for _, v in needs["genes"]]
    cells = [w for w, _ in needs["cells"]] + [w for w, _ in needs["unlabelled"]]
    tiers = []
    if disease and (genes or cells):
        tiers.append(f"{base} AND {_or(disease)} AND {_or(genes + cells)}")
    if disease:
        tiers.append(f"{base} AND {_or(disease)}")
    if genes or cells:
        tiers.append(f"{base} AND {_or(genes + cells)}")
    tiers.append(base)
    return list(dict.fromkeys(tiers))


def geo_query(needs: dict[str, list[tuple[str, str]]]) -> tuple[str, str]:
    query = geo_queries(needs)[0]
    return query, f"https://www.ncbi.nlm.nih.gov/gds/?term={quote_plus(query)}"


def classify(record: dict, needs_words: Sequence[str]) -> PublicDataset:
    text = f"{record.get('title', '')} {record.get('summary', '')}"
    lower = text.lower()
    technology = next((name for name, pattern in TECHNOLOGIES if re.search(pattern, lower)), "Other")
    accession = str(record.get("accession", ""))
    try:
        samples = int(record.get("n_samples")) if record.get("n_samples") not in (None, "") else None
    except (TypeError, ValueError):
        samples = None
    summary = re.sub(r"\s+", " ", str(record.get("summary", ""))).strip()
    return PublicDataset(
        accession=accession, title=str(record.get("title", "")).strip(), summary=summary[:420] + ("…" if len(summary) > 420 else ""),
        samples=samples, published=record.get("pdat") or None, technology=technology,
        auditable_here=technology == "Xenium" and "homo sapiens" in str(record.get("taxon", "Homo sapiens")).lower(),
        matches=[w for w in needs_words if re.search(rf"(?<![a-z0-9]){re.escape(w.lower())}", lower)],
        url=f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}",
    )


async def search_public(fit: DataFit, question: str, vocabulary: dict[str, str], searcher: Searcher) -> DataFit:
    """Fill `datasets` from the first query tier GEO returns records for. A failed search leaves the link to run it."""
    needs = read_needs(question, vocabulary)
    words = [v for _, v in needs["genes"]] + [w for w, _ in needs["cells"] + needs["unlabelled"]] + \
            [v for _, v in needs["diseases"] + needs["groups"] + needs["organs"]] + ["Xenium", "spatial"]
    found: dict[str, PublicDataset] = {}
    used: list[str] = []
    queries = geo_queries(needs)
    for query in queries:
        try:
            records = await searcher(query)
        except Exception as error:  # noqa: BLE001 - any failure: say so and keep the link
            if found:
                break
            return fit.model_copy(update={"search_note": f"GEO could not be searched just now ({type(error).__name__}); the link runs the same search."})
        if records:
            used.append(query)
        for record in records:
            if str(record.get("accession", "")) == fit.dataset_id:
                continue  # already in the workspace
            dataset = classify(record, words)
            found.setdefault(dataset.accession, dataset)
        if len(found) >= MIN_DATASETS:
            break
    if not used:
        return fit.model_copy(update={"search_note": "GEO returned no record for any form of the query."})
    query = used[0]
    note = "GEO records for the full query" if query == queries[0] else f"Nothing matched every need, so a broader GEO query: {query}"
    note += "; topped up from broader queries." if len(used) > 1 else "."
    datasets = sorted(found.values(), key=lambda d: (not d.auditable_here, -len(d.matches)))
    return fit.model_copy(update={"datasets": datasets, "search_note": note, "search_query": query,
                                  "search_url": f"https://www.ncbi.nlm.nih.gov/gds/?term={quote_plus(query)}"})


class GeoSearch:
    """NCBI E-utilities: esearch on GEO DataSets (db=gds), then esummary for the top records. Cached per query."""

    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, limit: int = 8, timeout: float = 10.0) -> None:
        self.limit, self.timeout = limit, timeout
        self._cache: dict[str, list[dict]] = {}

    async def __call__(self, query: str) -> list[dict]:
        if query in self._cache:
            return self._cache[query]
        import httpx2 as httpx

        async with httpx.AsyncClient(timeout=self.timeout, headers={"user-agent": "SpatialScout/1.0 (data check)"}) as client:

            async def get(path: str, params: dict):
                # NCBI allows 3 requests a second without a key: pace them, and wait once on a 429.
                for attempt in range(2):
                    await asyncio.sleep(0.4)
                    response = await client.get(f"{self.BASE}/{path}", params=params)
                    if response.status_code != 429 or attempt:
                        response.raise_for_status()
                        return response
                    await asyncio.sleep(1.2)
                raise AssertionError("unreachable")

            found = await get("esearch.fcgi", {"db": "gds", "term": query, "retmax": self.limit, "retmode": "json"})
            ids = found.json().get("esearchresult", {}).get("idlist", [])
            records: list[dict] = []
            if ids:
                summary = await get("esummary.fcgi", {"db": "gds", "id": ",".join(ids), "retmode": "json"})
                result = summary.json().get("result", {})
                records = [result[i] for i in result.get("uids", []) if i in result]
        if len(self._cache) > 200:
            self._cache.clear()
        self._cache[query] = records
        return records
