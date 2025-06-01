"""
Main FastAPI application file.
"""

import os
import time
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agents.postgres import get_checkpointer
from agents.workflows.whatsapp.tasks.meeting_reminder_task import meeting_reminder_task
from helpers.index import convert_seconds_to_hms
from middleware.logging_middlewares import (
    LoggingMiddleware,
    TraceIDMiddleware,
)
from routes.stream_routes import router as stream_router
from routes.user_routes import router as user_router
from routes.whatsapp_routes import router as whatsapp_router
from routes.workflow_routes import router as workflow_router
from services.prometheus import setup_prometheus

# Configure warning filters for external library deprecations we can't control
# Can be disabled by setting SUPPRESS_DEPRECATION_WARNINGS=false
if os.getenv("SUPPRESS_DEPRECATION_WARNINGS", "true").lower() == "true":
    # Suppress FAISS/numpy deprecation warnings
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="faiss.*",
        message=".*numpy.core._multiarray_umath.*",
    )
    # Suppress SWIG-related deprecation warnings
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*builtin type.*has no __module__ attribute.*",
    )
    # Suppress any remaining numpy core deprecations
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, message=".*numpy.core.*"
    )

load_dotenv(override=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("INFO: Initializing checkpointer at startup...")
    try:
        checkpointer = get_checkpointer()
        if (
            checkpointer
        ):  # Ensure checkpointer is not None (e.g. if DATABASE_URL is not set)
            print("INFO: Checkpointer initialized successfully.")
        else:
            print(
                "WARNING: Checkpointer is None, possibly due to missing DATABASE_URL. Skipping setup."
            )
    except Exception as e:
        print(f"ERROR: Failed to initialize checkpointer at startup: {e}")

    # Start the meeting reminder task
    print("INFO: Starting meeting reminder task...")
    meeting_reminder_task.start()
    print("INFO: Meeting reminder task started successfully.")

    yield

    # Shutdown
    print("INFO: Application shutting down...")
    meeting_reminder_task.stop()
    print("INFO: Meeting reminder task stopped.")


# FastAPI app configuration
app_config = {
    "title": "Orbia Backend API",
    "description": "AI-powered backend services for Orbia",
    "version": "1.0.0",
    "lifespan": lifespan,
}

# In production, disable docs unless explicitly enabled
if (
    os.getenv("NODE_ENV") == "production"
    and os.getenv("ENABLE_DOCS", "false").lower() != "true"
):
    app_config.update(
        {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }
    )

app = FastAPI(**app_config)


setup_prometheus(app, add_custom_metrics=True)

cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
# if os.getenv("DISABLE_AUTH", "false").lower() != "true":
#     app.add_middleware(AuthMiddleware)
app.add_middleware(TraceIDMiddleware)


@app.exception_handler(HTTPException)
async def log_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(workflow_router, prefix="/workflow", tags=["Workflow"])
app.include_router(stream_router, prefix="/stream", tags=["Stream"])
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])
app.include_router(user_router, prefix="/user", tags=["User"])

start_time = time.time()


@app.get("/_Health")
async def health_check():
    uptime_seconds = time.time() - start_time
    health_check_response = {
        "status": "UP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": convert_seconds_to_hms(uptime_seconds),
    }
    return health_check_response
