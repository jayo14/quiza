from enum import Enum


class ErrorCategory(Enum):
    TRANSIENT = "transient"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    INVALID_REQUEST = "invalid_request"
    CONTEXT_LENGTH = "context_length"
    SERVER_ERROR = "server_error"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"


def classify_error(exc: Exception) -> ErrorCategory:
    msg = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)

    if status in (401, 403) or "authentication" in msg or "invalid api key" in msg or "unauthorized" in msg:
        return ErrorCategory.AUTH_ERROR
    if (
        status in (404, 410)
        or "404" in msg
        or "410" in msg
        or "not found" in msg
        or "end of life" in msg
        or "no longer available" in msg
        or "does not exist" in msg
        or "model_not_found" in msg
    ):
        return ErrorCategory.MODEL_NOT_FOUND
    if status == 429 or "rate_limit" in msg or "rate limit" in msg or "quota" in msg or "resource_exhausted" in msg:
        return ErrorCategory.RATE_LIMITED
    if status == 400 or "invalid request" in msg or "bad request" in msg:
        return ErrorCategory.INVALID_REQUEST
    if "context" in msg and ("length" in msg or "too long" in msg or "exceed" in msg):
        return ErrorCategory.CONTEXT_LENGTH
    if status in (502, 503) or "unavailable" in msg or "high demand" in msg or "temporarily overloaded" in msg:
        return ErrorCategory.PROVIDER_UNAVAILABLE
    if status in (500,) or "server error" in msg:
        return ErrorCategory.SERVER_ERROR
    if "timeout" in msg or "timed out" in msg or "connection" in msg or "eof" in msg:
        return ErrorCategory.TRANSIENT
    if "503" in msg or "429" in msg:
        return ErrorCategory.RATE_LIMITED

    return ErrorCategory.UNKNOWN


def should_failover(exc: Exception) -> bool:
    cat = classify_error(exc)
    return cat in (
        ErrorCategory.TRANSIENT,
        ErrorCategory.RATE_LIMITED,
        ErrorCategory.SERVER_ERROR,
        ErrorCategory.PROVIDER_UNAVAILABLE,
        ErrorCategory.MODEL_NOT_FOUND,
        ErrorCategory.UNKNOWN,
    )
