"""Seam 1: descriptive disease contrasts on hand-built sections whose answers are known by construction.

Each hand-built section has 20 podocytes (the population gate's minimum) and places molecules of the result's gene
(NPHS1) and of another gene (ACTB) into four bins, which fixes what every primary condition keeps:

- nuclear: kept by every condition
- non-nuclear, 0.5 µm from the nucleus: kept by default and both distance caps
- non-nuclear, 1.5 µm from the nucleus: kept by default and the 2 µm cap
- non-nuclear, 5 µm from the nucleus: kept by default only

The library size is the population's pseudobulk total under the condition; the value is log2(CP10K + 1); the effect
is the disease group's mean value minus the control group's (spec, "Contrast effects").
"""

import math

import pytest

from spatialscout.contracts import ConditionName, Contrast, EvidenceStatus, StructureMask
from spatialscout.data import make_section
from spatialscout.engine import PRIMARY_CONDITIONS, compute_contrast

DEFAULT = ConditionName.DEFAULT
NUCLEUS_ONLY = ConditionName.NUCLEUS_ONLY
CAP_1 = ConditionName.DISTANCE_CAP_1UM
CAP_2 = ConditionName.DISTANCE_CAP_2UM
STRUCTURE = ConditionName.STRUCTURE_CONSTRAINED
DKD_VS_CONTROL = Contrast(disease="DKD", control="Control")
BINS = {"nuclear": (True, 0.0), "cap1": (False, 0.5), "cap2": (False, 1.5), "far": (False, 5.0)}


def section(section_id: str, gene: dict[str, int], other: dict[str, int], cells: int = 20, structures=()):
    """`gene` and `other` give molecule counts per bin, spread round-robin over the podocytes."""
    rows, i = [], 0
    for name, bins in (("NPHS1", gene), ("ACTB", other)):
        for bin_name, count in bins.items():
            nuclear, distance = BINS[bin_name]
            for _ in range(count):
                rows.append({"molecule_id": f"{section_id}-m{i}", "gene": name, "cell_id": f"c{i % cells}", "overlaps_nucleus": nuclear,
                             "nucleus_distance": distance, "x": 10.0, "y": 10.0, "qv": 40.0})
                i += 1
    return make_section(
        section_id, "hand-built", "hand-built",
        molecules=rows,
        cells=[{"cell_id": f"c{k}", "cell_type": "Podocyte", "x": 10.0, "y": 10.0, "nucleus_area": 28.3, "cell_area": 201.1} for k in range(cells)],
        structures=structures,
    )


def contrast(control, disease, conditions=PRIMARY_CONDITIONS):
    sections = [*control, *disease]
    groups = {s.section_id: "Control" for s in control} | {s.section_id: "DKD" for s in disease}
    return compute_contrast(sections, groups, DKD_VS_CONTROL, "Podocyte", "NPHS1", conditions,
                            inference_reason="Descriptive only (hand-built).", donor_distinctness="hand_built")


def effect(result, condition):
    return next(e for e in result.effects if e.condition == condition)


def test_values_are_library_size_normalised_log2_cp10k_plus_one_and_the_effect_is_the_difference_of_group_means():
    # Control: 15 NPHS1 of 10,000 molecules -> CP10K 15 -> log2(16) = 4.
    # DKD: 63 of 10,000 -> CP10K 63 -> log2(64) = 6; under nucleus-only 31 of 5,000 -> CP10K 62 -> log2(63).
    control = [section(f"C{k}", {"nuclear": 15}, {"far": 9985}) for k in range(2)]
    disease = [section(f"D{k}", {"nuclear": 31, "far": 32}, {"nuclear": 4969, "far": 4968}) for k in range(2)]

    result = contrast(control, disease)

    values = {(v.section_id, v.condition): v for v in result.per_section}
    assert values[("C0", DEFAULT)].library_size == 10_000
    assert values[("C0", DEFAULT)].log2_value == pytest.approx(4.0)
    assert values[("D0", DEFAULT)].log2_value == pytest.approx(6.0)
    assert values[("D0", NUCLEUS_ONLY)].library_size == 5_000
    assert values[("D0", NUCLEUS_ONLY)].log2_value == pytest.approx(math.log2(63))
    # Control under nucleus-only: 15 of 15 -> CP10K 10,000.
    assert values[("C0", NUCLEUS_ONLY)].log2_value == pytest.approx(math.log2(10_001))
    assert effect(result, DEFAULT).effect == pytest.approx(2.0)
    assert effect(result, NUCLEUS_ONLY).effect == pytest.approx(math.log2(63) - math.log2(10_001))
    assert result.inference_eligibility == "descriptive_only"
    assert result.rules is not None and result.rules.near_zero_band_log2 == 0.1


def test_a_failed_population_gate_makes_the_result_insufficient_evidence():
    control = [section("C0", {"nuclear": 20}, {"nuclear": 980}), section("C1", {"nuclear": 20}, {"nuclear": 980}, cells=19)]
    disease = [section(f"D{k}", {"nuclear": 40}, {"nuclear": 960}) for k in range(2)]

    result = contrast(control, disease)

    assert result.label == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert "population gate" in result.label_reason
    assert [s.section_id for s in result.sections if not s.passes_population_gate] == ["C1"]


def test_a_molecule_gate_failing_in_one_section_makes_only_that_condition_invalid():
    # D1 keeps 5 NPHS1 under nucleus-only (below the gate of 10), 15 under the 1 µm cap and 35 elsewhere.
    control = [section(f"C{k}", {"nuclear": 20}, {"nuclear": 980}) for k in range(2)]
    disease = [section("D0", {"nuclear": 40}, {"nuclear": 960}), section("D1", {"nuclear": 5, "cap1": 10, "cap2": 20}, {"nuclear": 965})]

    result = contrast(control, disease)

    assert {e.condition for e in result.effects if not e.valid} == {NUCLEUS_ONLY}
    assert "D1" in effect(result, NUCLEUS_ONLY).invalid_reason
    assert result.valid_conditions == [DEFAULT, CAP_1, CAP_2]


def test_fewer_than_two_valid_primary_conditions_is_insufficient_evidence():
    # Every disease NPHS1 molecule lies 5 µm from the nucleus, so only the default condition keeps any.
    control = [section(f"C{k}", {"nuclear": 20}, {"nuclear": 980}) for k in range(2)]
    disease = [section(f"D{k}", {"far": 40}, {"nuclear": 960}) for k in range(2)]

    result = contrast(control, disease)

    assert result.valid_conditions == [DEFAULT]
    assert result.label == EvidenceStatus.INSUFFICIENT_EVIDENCE


def test_a_consistent_effect_is_stable():
    # Control 100 then 200 CP10K, DKD 200 then 400: about +1 log2 under every condition.
    control = [section(f"C{k}", {"nuclear": 20}, {"nuclear": 980, "far": 1000}) for k in range(2)]
    disease = [section(f"D{k}", {"nuclear": 40}, {"nuclear": 960, "far": 1000}) for k in range(2)]

    result = contrast(control, disease)

    assert result.label == EvidenceStatus.STABLE
    assert all(e.direction == 1 for e in result.effects)


def test_a_near_zero_effect_is_never_counted_as_a_reversal():
    # Default: DKD 210 vs Control 200 CP10K (+0.07 log2); nucleus-only: 190 vs 200 (-0.07). Both inside ±0.1.
    control = [section(f"C{k}", {"nuclear": 20, "far": 20}, {"nuclear": 980, "far": 980}) for k in range(2)]
    disease = [section(f"D{k}", {"nuclear": 19, "far": 23}, {"nuclear": 981, "far": 977}) for k in range(2)]

    result = contrast(control, disease)

    assert effect(result, DEFAULT).effect == pytest.approx(math.log2(211 / 201))
    assert effect(result, NUCLEUS_ONLY).effect == pytest.approx(math.log2(191 / 201))
    assert {e.direction for e in result.effects} == {0}
    assert result.label == EvidenceStatus.STABLE


def test_a_genuine_reversal_is_segmentation_sensitive():
    # Default: DKD 250 vs Control 100 CP10K (+1.3 log2); nucleus-only: 100 vs 200 (-1.0).
    control = [section(f"C{k}", {"nuclear": 20}, {"nuclear": 980, "far": 1000}) for k in range(2)]
    disease = [section(f"D{k}", {"nuclear": 10, "far": 40}, {"nuclear": 990, "far": 960}) for k in range(2)]

    result = contrast(control, disease)

    assert effect(result, DEFAULT).direction == 1
    assert effect(result, NUCLEUS_ONLY).direction == -1
    assert result.label == EvidenceStatus.SEGMENTATION_SENSITIVE


def test_a_leave_one_section_out_flip_is_insufficient_evidence():
    # The same effect under every condition (all molecules nuclear), driven by D2: DKD mean log2 values
    # (2 x log2 51 + log2 1001) / 3 > log2 101, but without D2 the DKD mean falls to log2 51 < log2 101.
    control = [section(f"C{k}", {"nuclear": 20}, {"nuclear": 1980}) for k in range(2)]
    disease = [section("D0", {"nuclear": 10}, {"nuclear": 1990}), section("D1", {"nuclear": 10}, {"nuclear": 1990}),
               section("D2", {"nuclear": 200}, {"nuclear": 1800})]

    result = contrast(control, disease)

    assert effect(result, DEFAULT).direction == 1
    flips = {(f.left_out_section_id, f.condition) for f in result.leave_one_section_out if f.direction_kept is False}
    assert ("D2", DEFAULT) in flips
    assert result.label == EvidenceStatus.INSUFFICIENT_EVIDENCE


def test_the_exploratory_condition_is_reported_apart_and_never_changes_the_label():
    square = StructureMask(structure_id="g1", section_id="X", kind="glomerulus", outline=[[0, 0], [100, 0], [100, 100], [0, 100]], source="sam-3.1")
    control = [section(f"C{k}", {"nuclear": 20}, {"nuclear": 980, "far": 1000}, structures=[square.model_copy(update={"section_id": f"C{k}"})]) for k in range(2)]
    disease = [section(f"D{k}", {"nuclear": 10, "far": 40}, {"nuclear": 990, "far": 960}, structures=[square.model_copy(update={"section_id": f"D{k}"})]) for k in range(2)]

    primary = contrast(control, disease)
    with_exploratory = contrast(control, disease, [*PRIMARY_CONDITIONS, STRUCTURE])

    assert with_exploratory.label == primary.label
    assert with_exploratory.effects == primary.effects
    assert STRUCTURE not in {v.condition for v in with_exploratory.per_section}
    assert {v.condition for v in with_exploratory.exploratory_per_section} == {STRUCTURE}
    assert [e.condition for e in with_exploratory.exploratory_effects] == [STRUCTURE]
    assert with_exploratory.exploratory_effects[0].effect is not None
