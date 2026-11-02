"""Analysis engine: every deterministic science operation behind the agent's tools."""

from .audit import audit_section
from .conditions import IMPLEMENTED_CONDITIONS, ConditionUnavailable, inclusion_mask
from .population import POPULATION_GATE_MIN_CELLS, audit_population

__all__ = [
    "IMPLEMENTED_CONDITIONS",
    "POPULATION_GATE_MIN_CELLS",
    "ConditionUnavailable",
    "audit_population",
    "audit_section",
    "inclusion_mask",
]
