"""Model gateway failures. Each `code` names the failure in error events and the audit log."""

from ..contracts import ModelCallRecord


class GatewayError(Exception):
    """A model call that produced no usable response."""

    code = "model_gateway_error"

    def __init__(self, message: str, record: ModelCallRecord | None = None) -> None:
        super().__init__(message)
        self.record = record


class StoredResponseMissing(GatewayError):
    """No stored response matches the request's cache key, and this source never calls a model."""

    code = "replay_miss"


class ModelOutputInvalid(GatewayError):
    """The response did not validate against its Pydantic model, even after the one repair attempt."""

    code = "model_output_invalid"


class ModelOutputTruncated(GatewayError):
    """Empty content with finish reason "length": the model spent its whole token cap reasoning."""

    code = "model_output_truncated"


class ProviderError(GatewayError):
    """The provider refused or failed the call. `retryable` marks failures worth failing over on."""

    code = "provider_error"

    def __init__(self, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class MissingApiKey(GatewayError):
    code = "missing_api_key"


class BudgetExhausted(GatewayError):
    """The live call's worst-case cost does not fit in what is left of today's budget."""

    code = "budget_exhausted"


class LiveRunRefused(GatewayError):
    """Live runs need the passcode, a configured budget and budget left today."""

    code = "live_run_refused"
