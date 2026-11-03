"""Assignment conditions as molecule subsets (ADR-0002).

Each condition is a boolean inclusion mask over a section's molecules. Every condition is a subset of the
default condition, so pseudobulk counts stay integers. Ticket 05 adds the distance caps, ticket 07 the
structure-constrained condition; register them in `_RULES`.
"""

from collections.abc import Callable

import numpy as np

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


_RULES: dict[ConditionName, Callable[[SectionTables], np.ndarray]] = {
    ConditionName.DEFAULT: _default,
    ConditionName.NUCLEUS_ONLY: _nucleus_only,
    ConditionName.DISTANCE_CAP_1UM: _distance_cap(1.0),
    ConditionName.DISTANCE_CAP_2UM: _distance_cap(2.0),
}

PRIMARY_CONDITIONS: tuple[ConditionName, ...] = (
    ConditionName.DEFAULT,
    ConditionName.NUCLEUS_ONLY,
    ConditionName.DISTANCE_CAP_1UM,
    ConditionName.DISTANCE_CAP_2UM,
)

IMPLEMENTED_CONDITIONS: tuple[ConditionName, ...] = tuple(_RULES)


def inclusion_mask(section: SectionTables, condition: ConditionName) -> np.ndarray:
    """Which molecules of the section count toward a cell under the condition."""
    rule = _RULES.get(condition)
    if rule is None:
        raise ConditionUnavailable(f"assignment condition {condition.value!r} is not implemented yet")
    return rule(section)
