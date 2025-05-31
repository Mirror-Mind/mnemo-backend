import json
import logging
import os
import sys
import traceback

# Set up logging format with structlog
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone

import structlog

# Define a context variable for storing the request object
request_var = ContextVar("request", default=None)

# Check for concise logging mode from environment variable
CONCISE_LOGGING = os.environ.get("CONCISE_LOGGING", "false").lower() == "true"

# Get log level from environment variable, default to INFO
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Map string log levels to logging constants
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Get the actual log level constant
ACTUAL_LOG_LEVEL = LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO)


def log_json(
    msg,
    data=None,
    process_time=None,
    status_code=None,
    level="info",
    user_id=None,
    include_traceback=False,
):
    request = request_var.get()
    if CONCISE_LOGGING:
        timestamp = (
            datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        ).strftime("%Y-%m-%d %H:%M:%S")
        parts = [f"{timestamp} | {level.upper()} | {msg}"]
        if request and request.method and request.url and request.url.path:
            parts.append(f"{request.method} {request.url.path}")

        if status_code:
            parts.append(f"status={status_code}")

        if data:
            parts.append(f"data={json.dumps(data)}")

        if include_traceback:
            tb = traceback.format_exc()
            if tb != "NoneType: None\n":
                parts.append(f"traceback={tb}")

        return " | ".join(parts)

    log_data = {
        "level": level,
        "ts": (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).isoformat(),
        "msg": msg,
        "platform": "cosmos",
    }

    if request:
        if request.headers.get("x-caller"):
            log_data["caller"] = request.headers.get("x-caller")
        if hasattr(request.state, "trace_id"):
            log_data["traceId"] = request.state.trace_id
        if request.url and request.url.path:
            log_data["path"] = request.url.path
        if request.headers.get("host"):
            log_data["host"] = request.headers.get("host")
        if request.method:
            log_data["method"] = request.method
        if request.headers.get("x-sessionId"):
            log_data["sessionId"] = request.headers.get("x-sessionId")

    # Include user_id either from parameter or from request state or headers
    if user_id:
        log_data["userId"] = user_id
    elif request and hasattr(request.state, "user_id"):
        log_data["userId"] = request.state.user_id
    elif request and request.headers.get("x-user-id"):
        log_data["userId"] = request.headers.get("x-user-id")

    if process_time:
        log_data["process_time"] = process_time

    if status_code:
        log_data["status_code"] = status_code

    if data is not None:
        log_data["data"] = data

    if include_traceback:
        tb = traceback.format_exc()
        if tb != "NoneType: None\n":
            log_data["traceback"] = tb

    return log_data


class CustomLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

        # Create logs directory if it doesn't exist
        # os.makedirs("logs", exist_ok=True)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        self.addHandler(console_handler)

        # File handler with rotation (max 20 MB, 3 backups)
        # file_handler = RotatingFileHandler(
        #     "logs/logs.log", maxBytes=20 * 1024 * 1024, backupCount=3
        # )
        # self.addHandler(file_handler)

        # Set log level from environment variable
        self.setLevel(ACTUAL_LOG_LEVEL)

    def debug(self, msg, *args, **kwargs):
        # Extract custom kwargs before passing to parent
        data = kwargs.pop("data", None)
        process_time = kwargs.pop("process_time", None)
        status_code = kwargs.pop("status_code", None)
        user_id = kwargs.pop("user_id", None)
        # Remove any other custom kwargs that might cause issues
        kwargs.pop("error", None)

        try:
            log_output = log_json(
                msg,
                data=data,
                process_time=process_time,
                status_code=status_code,
                level="debug",
                user_id=user_id,
            )
        except Exception as e:
            log_output = f"Error logging debug: {str(e)}"

        if CONCISE_LOGGING:
            super().debug(log_output, *args, **kwargs)
        else:
            super().debug(json.dumps(log_output), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        # Extract custom kwargs before passing to parent
        data = kwargs.pop("data", None)
        process_time = kwargs.pop("process_time", None)
        status_code = kwargs.pop("status_code", None)
        user_id = kwargs.pop("user_id", None)
        # Remove any other custom kwargs that might cause issues
        kwargs.pop("error", None)

        try:
            log_output = log_json(
                msg,
                data=data,
                process_time=process_time,
                status_code=status_code,
                level="info",
                user_id=user_id,
            )
        except Exception as e:
            log_output = f"Error logging info: {str(e)}"

        if CONCISE_LOGGING:
            super().info(log_output, *args, **kwargs)
        else:
            super().info(json.dumps(log_output), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        # Extract custom kwargs before passing to parent
        data = kwargs.pop("data", None)
        status_code = kwargs.pop("status_code", None)
        user_id = kwargs.pop("user_id", None)
        include_traceback = kwargs.pop(
            "include_traceback", True
        )  # Default to True for errors
        # Remove any other custom kwargs that might cause issues
        kwargs.pop("error", None)  # Remove 'error' kwarg if present
        try:
            log_output = log_json(
                msg,
                level="error",
                data=data,
                status_code=status_code,
                user_id=user_id,
                include_traceback=include_traceback,
            )
        except Exception as e:
            log_output = f"Error logging error: {str(e)}"

        if CONCISE_LOGGING:
            super().error(log_output, *args, **kwargs)
        else:
            super().error(json.dumps(log_output), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        # Extract custom kwargs before passing to parent
        data = kwargs.pop("data", None)
        status_code = kwargs.pop("status_code", None)
        user_id = kwargs.pop("user_id", None)
        # Remove any other custom kwargs that might cause issues
        kwargs.pop("error", None)

        try:
            log_output = log_json(
                msg,
                level="warn",
                data=data,
                status_code=status_code,
                user_id=user_id,
            )
        except Exception as e:
            log_output = f"Error logging warning: {str(e)}"

        if CONCISE_LOGGING:
            super().warning(log_output, *args, **kwargs)
        else:
            super().warning(json.dumps(log_output), *args, **kwargs)

    def exception(
        self,
        msg,
        *args,
        **kwargs,
    ):
        data = kwargs.pop("data", None)
        user_id = kwargs.pop("user_id", None)
        include_traceback = kwargs.pop(
            "include_traceback", True
        )  # Default to True for exceptions

        try:
            msg_info = log_json(
                msg,
                level="exception",
                data=data,
                user_id=user_id,
                include_traceback=include_traceback,
            )
            super().exception(json.dumps(msg_info), *args, **kwargs)
        except Exception as e:
            msg_info = f"Error logging exception: {str(e)}"
            super().exception(msg_info, *args, **kwargs)


def setup_logging():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            lambda logger, method_name, event_dict: event_dict.update(
                msg=event_dict.pop("event", "")
            )
            or event_dict,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),  # Output logs as JSON
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=ACTUAL_LOG_LEVEL,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Ensures previous log configurations are overridden
    )


logger = CustomLogger(name="custom_logger", level=ACTUAL_LOG_LEVEL)
