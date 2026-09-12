"""Turns the domain exceptions into HTTP responses. The only place in the kernel that knows about FastAPI."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError, envelope


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=envelope(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = {"errors": [{"loc": list(e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()]}
        return JSONResponse(status_code=422, content=envelope("validation_error", "request failed validation", details))
