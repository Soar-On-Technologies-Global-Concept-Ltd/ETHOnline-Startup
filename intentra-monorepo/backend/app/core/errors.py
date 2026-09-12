"""The failures the domains raise, and the one envelope every one of them is reported in (section 18).

Deliberately free of FastAPI: policy, the state machine and the domain services raise these, and none of them
should have to know that a web framework exists. The handler wiring lives in core/error_handlers.py.
"""
from typing import Any


class AppError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str | None = None, *, code: str | None = None, details: dict[str, Any] | None = None,
                 status: int | None = None):
        super().__init__(message or code or self.code)
        self.message = message or (code or self.code).replace("_", " ")
        self.code = code or self.code
        self.details = details or {}
        if status:
            self.status = status


class Unauthorized(AppError):
    status, code = 401, "invalid_token"


class Forbidden(AppError):
    status, code = 403, "not_party"


class NotFound(AppError):
    status, code = 404, "not_found"


class Conflict(AppError):
    status, code = 409, "illegal_transition"


class Gone(AppError):
    status, code = 410, "expired"


class PayloadTooLarge(AppError):
    status, code = 413, "file_too_large"


class UnsupportedMedia(AppError):
    status, code = 415, "unsupported_media_type"


class Unprocessable(AppError):
    status, code = 422, "validation_error"


class UpstreamVerificationFailed(AppError):
    status, code = 424, "upstream_verification_failed"


class DependencyUnavailable(AppError):
    status, code = 503, "dependency_unavailable"


class AITimeout(AppError):
    status, code = 504, "ai_timeout"


def envelope(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}
