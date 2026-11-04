"""Seam 2: the data check through the HTTP API. The question's needs are read in code against the committed
GSE286184 and KPMP artifacts; GEO is replaced by a fake searcher (the network is blocked in tests)."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from spatialscout.api import create_app

from .conftest import REPO, make_settings

FEATURED = (
    "My hypothesis: the podocytes this atlas calls 'endocytic' really carry LRP2, and the UMOD seen in B cells is "
    "spillover from neighbouring thick ascending limb cells. Does each part hold up under stricter assignment?"
)


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(replace(make_settings(tmp_path), artifacts_dir=REPO / "artifacts"))) as test_client:
        yield test_client


class FakeGeo:
    def __init__(self, records_for=lambda q: []):
        self.queries: list[str] = []
        self.records_for = records_for

    async def __call__(self, query: str) -> list[dict]:
        self.queries.append(query)
        return self.records_for(query)


def fit(client, question, geo=None, search=True):
    client.app.state.public_search = geo or FakeGeo()
    response = client.post("/api/data-fit", json={"question": question, "search": search})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_recorded_hypothesis_needs_nothing_the_workspace_lacks(client):
    body = fit(client, FEATURED, search=False)
    assert body["answerable"] and body["gaps"] == []
    assert {(m["kind"], m["value"]) for m in body["matched"]} >= {("gene", "LRP2"), ("gene", "UMOD"), ("cell_type", "Podocyte"),
                                                                 ("cell_type", "B cell"), ("cell_type", "TAL")}
    assert FEATURED in body["related_recordings"]


def test_a_gene_off_the_panel_is_a_hard_gap_and_an_absent_disease_a_soft_one(client):
    body = fit(client, "Is APOL1 in podocytes higher in FSGS?", search=False)
    gaps = {(g["kind"], g["item"]): g["hard"] for g in body["gaps"]}
    assert gaps == {("gene", "APOL1"): True, ("group", "FSGS"): False}
    assert not body["answerable"]
    assert body["upload_prefill"] == {"cell_type": "Podocyte", "genes": ["APOL1"]}
    assert any("APOL1" in n for n in body["upload_needs"])


@pytest.mark.parametrize(("question", "kind", "item"), [
    ("Does UMOD in B cells hold in mouse kidney?", "species", "mouse"),
    ("Which hepatocytes express ALB in the liver?", "organ", "liver"),
    ("Do plasma cells carry IGHG1 here?", "cell_type", "plasma cell"),
    ("Is chromatin accessibility at NPHS1 lower in DKD?", "assay", "chromatin accessibility"),
])
def test_another_species_organ_cell_type_or_assay_cannot_be_answered_here(client, question, kind, item):
    body = fit(client, question, search=False)
    assert not body["answerable"]
    assert any(g["kind"] == kind and g["item"] == item and g["hard"] for g in body["gaps"])


def test_genes_are_read_by_symbol_alias_or_protein_name_and_never_from_ordinary_words(client):
    body = fit(client, "does nphs1 in podocytes survive? And megalin? What about CD20 in AKI, and IS THE SET OK?", search=False)
    genes = {m["value"] for m in body["matched"] if m["kind"] == "gene"}
    assert genes == {"NPHS1", "LRP2", "MS4A1"}
    assert body["answerable"]
    aki = next(g for g in body["gaps"] if g["item"] == "AKI")
    assert not aki["hard"] and "KPMP holds 1 AKI biopsy" in aki["why"]


def test_public_datasets_are_geo_records_with_their_technology_read_and_xenium_first(client):
    records = [
        {"accession": "GSE1", "title": "Visium of FSGS kidney", "summary": "podocyte loss", "n_samples": "6", "pdat": "2025/01/01"},
        {"accession": "GSE2", "title": "Xenium in situ of human kidney", "summary": "APOL1 risk variants in podocytes", "n_samples": "12", "pdat": "2025/06/01", "taxon": "Homo sapiens"},
        {"accession": "GSE3", "title": "Xenium of mouse kidney", "summary": "", "taxon": "Mus musculus"},
        {"accession": "GSE286184", "title": "Xenium of human glomerular disease", "summary": "the workspace's own"},
    ]
    geo = FakeGeo(lambda q: records if "FSGS" in q else [])
    body = fit(client, "Is APOL1 in podocytes higher in FSGS?", geo)
    assert [d["accession"] for d in body["datasets"]] == ["GSE2", "GSE1", "GSE3"]
    assert not body["datasets"][2]["auditable_here"]  # mouse Xenium: the label rules are human
    first = body["datasets"][0]
    assert first["technology"] == "Xenium" and first["auditable_here"] and first["samples"] == 12
    assert set(first["matches"]) >= {"APOL1", "podocyte"}
    assert body["datasets"][1]["technology"] == "Visium" and not body["datasets"][1]["auditable_here"]
    assert "FSGS" in body["search_query"] and body["search_url"].startswith("https://www.ncbi.nlm.nih.gov/gds/")


def test_the_search_broadens_until_geo_returns_records_and_survives_a_failure(client):
    geo = FakeGeo(lambda q: [{"accession": "GSE9", "title": "spatial kidney", "summary": ""}] if "FSGS" not in q and "APOL1" not in q else [])
    body = fit(client, "Is APOL1 in podocytes higher in FSGS?", geo)
    assert len(geo.queries) == 4 and [d["accession"] for d in body["datasets"]] == ["GSE9"]
    assert "broader" in body["search_note"]

    async def down(query):
        raise TimeoutError

    client.app.state.public_search = down
    body = client.post("/api/data-fit", json={"question": "Is APOL1 in podocytes higher in FSGS?"}).json()
    assert body["datasets"] == [] and "could not be searched" in body["search_note"] and "FSGS" in body["search_url"]


@pytest.mark.parametrize("question", [
    "Is CD3 in T cells stable?", "CD8 T cells", "CD31 in endothelium", "CD45 cells", "aSMA in vessels",
    "smooth muscle actin in vessels", "Podocalyxin+ cells", "collecting duct principal cells", "CKD5 biopsies",
    "UMOD in TAL cells in DKD", "G3a CKD with A2 albuminuria",
])
def test_the_words_the_biopsy_screens_show_never_block_a_question(client, question):
    body = fit(client, question, search=False)
    assert body["answerable"], body["gaps"]


def test_a_protein_imaged_on_kpmp_points_to_the_biopsy_and_does_not_block(client):
    body = fit(client, "Is Podocalyxin in glomeruli lower in CKD?", search=False)
    gap = next(g for g in body["gaps"] if g["item"] == "PODXL")
    assert not gap["hard"] and "draw a box" in gap["why"]
