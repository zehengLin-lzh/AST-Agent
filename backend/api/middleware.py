"""FastAPI middleware: request_id + structured access logging."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.observability import (
    bind_context,
    clear_context,
    get_logger,
    log_event,
    new_request_id,
    request_id_var,
)

log = get_logger("api.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request_id, log access, and expose it via response header.

    Honours an inbound ``X-Request-ID`` header for tracing across services;
    otherwise generates a short random id.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        inbound = request.headers.get("x-request-id")
        rid = inbound or new_request_id()
        if inbound:
            request_id_var.set(inbound)

        bind_context(
            method=request.method,
            path=request.url.path,
        )

        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            log_event(log, "request.complete", status=500, duration_ms=duration_ms)
            log.exception("request.unhandled_exception")
            clear_context()
            raise

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        log_event(
            log,
            "request.complete",
            status=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = rid
        clear_context()
        return response
