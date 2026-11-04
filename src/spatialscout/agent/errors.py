"""Investigation failures. Each `code` appears in the error event and the audit log."""


class InvestigationError(Exception):
    code = "investigation_error"


class RunModeUnavailable(InvestigationError):
    code = "run_mode_unavailable"


class PlanInvalid(InvestigationError):
    code = "plan_invalid"


class DatasetUnavailable(InvestigationError):
    code = "dataset_unavailable"


class InvalidRegions(InvestigationError):
    """A region drawn in the viewer is not on a section of the investigated dataset."""

    code = "invalid_regions"


class PlanUnsupported(InvestigationError):
    """The planner's proposal failed the registry and capability checks twice; the investigation reports the limitation."""

    code = "plan_unsupported"


class ToolCallInvalid(ValueError):
    """A tool call the registry, its arguments contract or the dataset cannot back."""


class UnknownInvestigation(KeyError):
    """No investigation with this id exists in the investigations directory."""


class NoRecordedInvestigation(InvestigationError):
    """Immutable replay was asked for a question with no recorded investigation."""

    code = "no_recorded_investigation"
