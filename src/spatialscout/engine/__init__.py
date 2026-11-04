"""Analysis engine: every deterministic science operation behind the agent's tools."""

from .audit import audit_section
from .channels import CHANNELS, section_channels
from .conditions import (
    EXPLORATORY_CONDITIONS,
    IMPLEMENTED_CONDITIONS,
    PRIMARY_CONDITIONS,
    ConditionUnavailable,
    conditions_for,
    inclusion_mask,
)
from .contrast import compute_contrast
from .controls import label_sensitivity_check, random_thinning_control
from .markers import HOME_CELL_TYPES, MarkerPairs, home_cell_type, load_marker_pairs
from .population import (
    MOLECULE_GATE_MIN_MOLECULES,
    MIN_ELIGIBLE_SECTIONS,
    POPULATION_GATE_MIN_CELLS,
    audit_population,
    gate_status,
    restrict_to_roi,
)
from .region import build_packed_region_view, build_region_view

__all__ = [
    "CHANNELS",
    "section_channels",
    "HOME_CELL_TYPES",
    "IMPLEMENTED_CONDITIONS",
    "MIN_ELIGIBLE_SECTIONS",
    "MOLECULE_GATE_MIN_MOLECULES",
    "POPULATION_GATE_MIN_CELLS",
    "PRIMARY_CONDITIONS",
    "ConditionUnavailable",
    "EXPLORATORY_CONDITIONS",
    "conditions_for",
    "MarkerPairs",
    "audit_population",
    "audit_section",
    "compute_contrast",
    "build_packed_region_view",
    "build_region_view",
    "gate_status",
    "home_cell_type",
    "inclusion_mask",
    "label_sensitivity_check",
    "load_marker_pairs",
    "random_thinning_control",
    "restrict_to_roi",
]
