import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("netbalance")


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Consistent JSON shape for all HTTP errors (4xx, 5xx).
    Includes the request_id so clients can reference it when reporting issues.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "status_code": exc.status_code,
                "detail": exc.detail,
                "request_id": request_id,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    FastAPI's 422 validation errors come in a verbose nested format by default.
    We flatten them into a clean list of human-readable messages.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "status_code": 422,
                "detail": "Validation failed",
                "errors": errors,
                "request_id": request_id,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback

    traceback.print_exception(type(exc), exc, exc.__traceback__)

    raise exc
