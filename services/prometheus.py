from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info

# Define global metrics with orbia namespace
# Workflow metrics
COSMOS_WORKFLOW_CALLS = Counter(
    "cosmos_workflow_calls_total",
    "Number of times a workflow has been called",
    labelnames=("user_id", "workflow_name", "status"),
)

COSMOS_WORKFLOW_LATENCY = Histogram(
    "cosmos_workflow_latency_seconds",
    "Latency of workflow execution",
    labelnames=("workflow_name",),
    buckets=(
        0.1,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        20.0,
        30.0,
        60.0,
        120.0,
        300.0,
        float("inf"),
    ),
)

# Error metrics
COSMOS_API_ERRORS = Counter(
    "cosmos_api_errors_total",
    "Number of API errors",
    labelnames=("endpoint", "error_type", "status_code"),
)

# Request metrics
COSMOS_REQUESTS_TOTAL = Counter(
    "cosmos_requests_total",
    "Number of requests",
    labelnames=("endpoint", "status_code"),
)

# Last activity timestamp
COSMOS_LAST_ACTIVITY = Gauge(
    "cosmos_last_activity_timestamp",
    "Timestamp of the last activity by a user",
    labelnames=("user_id",),
)

# List of endpoints to exclude from metrics collection
EXCLUDED_ENDPOINTS = ["/metrics", "/_Health", "/docs", "/redoc", "/openapi.json"]


def setup_prometheus(app: FastAPI, add_custom_metrics=True):
    """
    Set up Prometheus instrumentation for a FastAPI application.

    Args:
        app: The FastAPI application to instrument
        add_custom_metrics: Whether to add custom metrics specific to the application

    Returns:
        The configured Instrumentator instance
    """
    # Initialize the instrumentator with configured parameters
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=EXCLUDED_ENDPOINTS,
    )

    if add_custom_metrics:
        _add_custom_metrics(instrumentator)

    # Instrument the app and expose the /metrics endpoint
    return instrumentator.instrument(app).expose(
        app, include_in_schema=False, should_gzip=True
    )


def _add_custom_metrics(instrumentator):
    """
    Add custom metrics via instrumentator for metrics that work better with request/response info
    """
    # Track in-progress requests
    instrumentator.add(in_progress_requests_metric())

    # Track request duration with detailed buckets (for API latency metrics)
    instrumentator.add(request_duration_histogram())


def request_duration_histogram():
    """
    Create a request duration histogram with custom buckets for API performance tracking.
    """
    METRIC = Histogram(
        "cosmos_http_request_duration_seconds",
        "HTTP request duration with custom buckets for better API performance tracking",
        labelnames=("method", "handler"),
        buckets=(
            0.01,
            0.05,
            0.1,
            0.25,
            0.5,
            0.75,
            1,
            2.5,
            5,
            7.5,
            10,
            30,
            60,
            float("inf"),
        ),
    )

    def instrumentation(info: Info) -> None:
        # Skip excluded endpoints
        if info.request.url.path in EXCLUDED_ENDPOINTS:
            return

        if info.modified_duration:
            METRIC.labels(
                method=info.request.method,
                handler=info.modified_handler,
            ).observe(info.modified_duration)

    return instrumentation


def in_progress_requests_metric():
    """Track the number of in-progress requests by endpoint."""
    IN_PROGRESS = Gauge(
        "cosmos_requests_in_progress",
        "Number of in-progress HTTP requests",
        labelnames=("method", "handler"),
    )

    def instrumentation(info: Info) -> None:
        # Skip excluded endpoints
        if info.request.url.path in EXCLUDED_ENDPOINTS:
            return

        # Use Gauge to track in-progress requests
        IN_PROGRESS.labels(
            method=info.request.method,
            handler=info.modified_handler,
        ).inc()

        if hasattr(info, "response") and info.response:
            IN_PROGRESS.labels(
                method=info.request.method,
                handler=info.modified_handler,
            ).dec()

    return instrumentation
