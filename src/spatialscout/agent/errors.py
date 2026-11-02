"""Investigation failures. Each `code` appears in the error event and the audit log."""


class InvestigationError(Exception):
    code = "investigation_error"


class RunModeUnavailable(InvestigationError):
    code = "run_mode_unavailable"


class PlanInvalid(InvestigationError):
    code = "plan_invalid"


class UnknownInvestigation(KeyError):
    """No investigation with this id exists in the investigations directory."""
