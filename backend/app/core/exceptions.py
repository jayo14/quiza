class QuizaError(Exception):
    """Base class for domain errors that map to a specific HTTP response."""

    status_code = 400
    detail = "Something went wrong."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(QuizaError):
    status_code = 404
    detail = "Resource not found."


class ForbiddenError(QuizaError):
    status_code = 403
    detail = "You do not have access to this resource."


class ConflictError(QuizaError):
    status_code = 409
    detail = "Resource already exists."


class UnauthorizedError(QuizaError):
    status_code = 401
    detail = "Invalid credentials."


class ValidationFailedError(QuizaError):
    status_code = 422
    detail = "Validation failed."


class RateLimitedError(QuizaError):
    status_code = 429
    detail = "Too many requests, please try again shortly."


class AIServiceError(QuizaError):
    """Raised when an upstream AI provider fails, times out, or returns output that
    cannot be salvaged into a valid structured response."""

    status_code = 502
    detail = "The AI service is temporarily unavailable."
