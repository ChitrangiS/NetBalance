from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.middleware.logging_middleware import RequestLoggingMiddleware, setup_logging
from app.middleware.error_middleware import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)

# Initialise structured logging BEFORE anything else — so even startup
# errors are captured in JSON format, not plain text
setup_logging()

app = FastAPI(
    title="NetBalance API",
    version="1.0.0",
    # /docs is useful for portfolio demos; disable for internal-only APIs
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (applied in reverse order — last added = outermost) ──────────────
# RequestLoggingMiddleware wraps everything: even error handler responses
# are captured in logs with timing information
app.add_middleware(RequestLoggingMiddleware)

# ── Exception handlers ─────────────────────────────────────────────────────────
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
#app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Versioned routers under /v1 ───────────────────────────────────────────────
# All existing endpoints now live under /v1/ — future breaking changes
# go to /v2/, while /v1/ remains available for existing clients.
from app.routers.v1 import auth, groups, expenses, balances, settlements  # noqa: E402

app.include_router(auth.router,        prefix="/v1")
app.include_router(groups.router,      prefix="/v1")
app.include_router(expenses.router,    prefix="/v1")
app.include_router(balances.router,    prefix="/v1")
app.include_router(settlements.router, prefix="/v1")


@app.get("/")
def root():
    return {"message": "NetBalance API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "ok"}