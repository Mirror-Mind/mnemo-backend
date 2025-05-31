import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from helpers.logger_config import logger


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()
        trace_id = getattr(request.state, "trace_id", "N/A")
        # Get user_id from request state (set by AuthMiddleware if present) or headers
        user_id = getattr(request.state, "user_id", None) or request.headers.get(
            "X-User-ID",
            "anonymous",  # Default to anonymous if not found
        )

        logger.info(
            f"Request started: {request.method} {request.url.path}",  # Combined message
            extra={
                "method": request.method,
                "url": str(request.url),
                "trace_id": trace_id,
                "user_id": user_id,
                "request_headers": dict(
                    request.headers
                ),  # Optional: log request headers
            },
        )

        response = await call_next(request)
        process_time_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            f"Request finished: {request.method} {request.url.path} - Status {response.status_code} in {process_time_ms}ms",  # Combined message
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time_ms": process_time_ms,
                "trace_id": trace_id,
                "user_id": user_id,
                "response_headers": dict(
                    response.headers
                ),  # Optional: log response headers
            },
        )
        return response
