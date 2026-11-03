"""Assignment conditions as molecule subsets (ADR-0002).

Each condition is a boolean inclusion mask over a section's molecules. Every condition is a subset of the
default condition, so pseudobulk counts stay integers. The primary conditions are default, nucleus-only and the
distance caps. The structure-constrained condition is exploratory (ADR-0006): it is computed and shown beside them,
needs the section's structure masks, and never enters an evidence label.
"""

from collections.abc import Callable

import numpy as np
from matplotlib.path import Path

from ..contracts import ConditionName
from ..data import SectionTables


class ConditionUnavailable(ValueError):
    """The condition cannot be computed for this section; it must be reported, never counted as evidence."""


def _default(section: SectionTables) -> np.ndarray:
    """The instrument's own assignment: every molecule assigned to a cell."""
    return section.molecules["cell_id"].notna().to_numpy(dtype=bool)


def _nucleus_only(section: SectionTables) -> np.ndarray:
    """Only molecules that overlap their cell's nucleus."""
    return _default(section) & section.molecules["overlaps_nucleus"].to_numpy(dtype=bool)


def _distance_cap(cap_um: float) -> Callable[[SectionTables], np.ndarray]:
    """Nuclear molecules plus non-nuclear ones within `cap_um` of the nucleus. A molecule without a nucleus
    distance (its cell has no detected nucleus) is never within a cap, so the cap excludes it."""

    def rule(section: SectionTables) -> np.ndarray:
        distance = section.molecules["nucleus_distance"].to_numpy(dtype=float)
        with np.errstate(invalid="ignore"):
            near = distance <= cap_um
        return _nucleus_only(section) | (_default(section) & near)

    return rule


def structure_index(section: SectionTables, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """For each point, the index of the first structure outline containing it, or -1 for none."""
    index = np.full(len(x), -1, dtype=np.int64)
    points = np.column_stack([x, y])
    for k, structure in enumerate(section.structures):
        if len(structure.outline) < 3:
            continue
        inside = (index < 0) & Path(np.asarray(structure.outline, dtype=float)).contains_points(points)
        index[inside] = k
    return index


def _structure_constrained(section: SectionTables) -> np.ndarray:
    """Default molecules whose position and whose cell's centroid lie on the same side of every structure outline:
    inside the same structure, or both outside all of them. Exploratory; needs the section's structure masks."""
    if not section.structures:
        raise ConditionUnavailable(
            f"section {section.section_id} has no structure masks, so the structure-constrained condition cannot be computed"
        )
    molecules, cells = section.molecules, section.cells
    cell_structure = structure_index(section, cells["x"].to_numpy(dtype=float), cells["y"].to_numpy(dtype=float))
    position = {cell_id: i for i, cell_id in enumerate(cells["cell_id"].astype(str))}
    cell_rows = molecules["cell_id"].astype("string").fillna("").map(lambda c: position.get(c, -1)).to_numpy(dtype=np.int64)
    molecule_structure = structure_index(section, molecules["x"].to_numpy(dtype=float), molecules["y"].to_numpy(dtype=float))
    has_cell = cell_rows >= 0
    same_side = np.zeros(len(molecules), dtype=bool)
    same_side[has_cell] = molecule_structure[has_cell] == cell_structure[cell_rows[has_cell]]
    return _default(section) & same_side


_RULES: dict[ConditionName, Callable[[SectionTables], np.ndarray]] = {
    ConditionName.DEFAULT: _default,
    ConditionName.NUCLEUS_ONLY: _nucleus_only,
    ConditionName.DISTANCE_CAP_1UM: _distance_cap(1.0),
    ConditionName.DISTANCE_CAP_2UM: _distance_cap(2.0),
    ConditionName.STRUCTURE_CONSTRAINED: _structure_constrained,
}

PRIMARY_CONDITIONS: tuple[ConditionName, ...] = (
    ConditionName.DEFAULT,
    ConditionName.NUCLEUS_ONLY,
    ConditionName.DISTANCE_CAP_1UM,
    ConditionName.DISTANCE_CAP_2UM,
)

EXPLORATORY_CONDITIONS: tuple[ConditionName, ...] = (ConditionName.STRUCTURE_CONSTRAINED,)

IMPLEMENTED_CONDITIONS: tuple[ConditionName, ...] = tuple(_RULES)


def conditions_for(section: SectionTables) -> list[ConditionName]:
    """The implemented conditions this section can compute, in enum order: the structure-constrained condition
    only when the section has structure masks."""
    return [c for c in ConditionName if c in _RULES and (c != ConditionName.STRUCTURE_CONSTRAINED or section.structures)]


def inclusion_mask(section: SectionTables, condition: ConditionName) -> np.ndarray:
    """Which molecules of the section count toward a cell under the condition."""
    rule = _RULES.get(condition)
    if rule is None:
        raise ConditionUnavailable(f"assignment condition {condition.value!r} is not implemented yet")
    return rule(section)
