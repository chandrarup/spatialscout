"""The data check: what a question needs against what the workspace holds, and public datasets for the rest."""

import json
from collections import Counter

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field

from ..contracts import Contract, DataFit
from ..lab.datafit import GeoSearch, check, gene_vocabulary, search_public
from ..settings import Settings

router = APIRouter()
DATASET_ID = "GSE286184"


class DataFitRequest(Contract):
    question: str = Field(min_length=3, max_length=2000)
    search: bool = True


def _workspace(settings: Settings) -> dict:
    root = settings.artifacts_dir
    assert root is not None
    manifest = json.loads((root / DATASET_ID / "manifest.json").read_text(encoding="utf-8"))
    rules = json.loads((root / DATASET_ID / "label_rules.json").read_text(encoding="utf-8"))
    rule = next(r for r in rules["rules"] if r["label_rule_id"] == rules["default_label_rule_id"])
    groups = Counter(s["group"] for s in manifest["sections"] if not s.get("duplicate_of"))
    kpmp_path = root / "KPMP" / "manifest.json"
    categories: Counter[str] = Counter()
    if kpmp_path.exists():
        kpmp = json.loads(kpmp_path.read_text(encoding="utf-8"))
        categories = Counter(p.get("clinical", {}).get("KPMP enrollment category", p["role"]) for p in kpmp["participants"])
    return {"panel": manifest["panel"], "cell_types": list(rule["markers"]), "groups": dict(sorted(groups.items())),
            "kpmp_categories": dict(categories)}


@router.post("/data-fit")
async def data_fit(body: DataFitRequest, request: Request) -> DataFit:
    """Read the question's needs (genes, cell types, disease groups, organ, species, assay) in code, set them against
    GSE286184 and the KPMP biopsies, and search GEO for public datasets that hold what is missing."""
    settings: Settings = request.app.state.settings
    root = settings.artifacts_dir
    vocabulary_path = root / "reference" / "hgnc_genes.tsv.gz" if root else None
    if root is None or vocabulary_path is None or not vocabulary_path.exists() or not (root / DATASET_ID / "manifest.json").exists():
        raise HTTPException(status_code=404, detail={"code": "no_workspace", "message": "The data check needs the GSE286184 artifacts and the gene list."})
    vocabulary = gene_vocabulary(vocabulary_path)
    recorded = [r.question for r in request.app.state.recordings.infos() if r.dataset_id == DATASET_ID]
    fit = check(body.question, vocabulary=vocabulary, dataset_id=DATASET_ID, recorded_questions=recorded, **_workspace(settings))
    if not body.search:
        return fit
    searcher = getattr(request.app.state, "public_search", None)
    if searcher is None:
        searcher = request.app.state.public_search = GeoSearch()
    return await search_public(fit, body.question, vocabulary, searcher)
