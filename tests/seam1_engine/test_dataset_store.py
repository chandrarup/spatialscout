"""Seam 1: the dataset store's GSE286184 sections, from the committed artifacts alone (no raw data needed)."""

from pathlib import Path

from spatialscout.data import DatasetStore

REPO = Path(__file__).resolve().parents[2]


def test_distinct_sections_count_the_duplicated_igan_pair_once():
    store = DatasetStore(REPO / "fixtures", artifacts_dir=REPO / "artifacts")

    distinct = [s.section_id for s in store.distinct_sections("GSE286184")]

    assert (len(store.sections("GSE286184")), len(distinct)) == (22, 21)
    assert "GSM8720418" in distinct and "GSM8720419" not in distinct
