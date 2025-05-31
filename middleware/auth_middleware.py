import base64
import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse

from helpers.logger_config import logger

load_dotenv()


# Custom Middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        try:
            if path == "/_Health" and method == "GET":
                response = await call_next(request)
                return response

            if method == "OPTIONS":
                response = await call_next(request)
                return response

            auth_header = request.headers.get("Authorization")
            if not auth_header:
                logger.error(
                    f"No Auth Token Found for {path}",
                    data={"path": path, "method": method},
                )
                return JSONResponse(
                    {"detail": {"message": "No Auth Token Found", "canRetry": False}},
                    status_code=401,
                )
            auth_header = request.headers.get("Authorization")
            try:
                if auth_header.startswith("Bearer "):
                    token_string = auth_header[len("Bearer ") :]
                    if path == "/metrics":
                        logger.error(
                            f"Invalid Auth Token type for metrics endpoint: {path}",
                            data={"path": path, "method": method},
                        )
                        return JSONResponse(
                            {
                                "detail": "Invalid Auth Token. Please provide a valid Basic Auth Token."
                            },
                            status_code=401,
                        )
                    try:
                        token_data = verify_token(
                            token_string, os.getenv("JWT_SECRET_KEY")
                        )
                    except ValueError as e:
                        logger.error(
                            f"JWT verification failed for {path}: {str(e)}",
                            data={"path": path, "method": method, "error": str(e)},
                        )
                        return JSONResponse({"detail": str(e)}, status_code=401)
                    # Single tenant setup - no longer extract tenant from token
                    request.state.user_id = token_data.get("userId", "default_user")
                    response = await call_next(request)
                    return response

                elif auth_header.startswith("Basic "):
                    token_string = auth_header[len("Basic ") :]
                    if path != "/metrics":
                        logger.error(
                            f"Invalid Auth Token type for non-metrics endpoint: {path}",
                            data={"path": path, "method": method},
                        )
                        return JSONResponse(
                            {
                                "detail": "Invalid Auth Token. Please provide a valid Bearer Auth Token."
                            },
                            status_code=401,
                        )
                    try:
                        decoded = base64.b64decode(token_string).decode("utf-8")
                        username, password = decoded.split(":", 1)
                        if username == os.getenv(
                            "PROMETHEUS_USERNAME"
                        ) and password == os.getenv("PROMETHEUS_PASSWORD"):
                            return await call_next(request)
                        else:
                            logger.error(
                                f"Invalid Basic Auth Credentials for {path}",
                                data={"path": path, "method": method},
                            )
                            return JSONResponse(
                                {"detail": "Invalid Basic Auth Credentials"},
                                status_code=401,
                            )
                    except Exception:
                        logger.error(
                            f"Invalid Basic Auth Format for {path}",
                            data={"path": path, "method": method},
                        )
                        return JSONResponse(
                            {"detail": "Invalid Basic Auth Format"}, status_code=401
                        )
            except ValueError as e:
                logger.error(
                    f"Auth Token validation failed for {path}: {str(e)}",
                    data={"path": path, "method": method, "error": str(e)},
                )
                return JSONResponse(
                    {"detail": {"message": str(e), "canRetry": False}}, status_code=401
                )

        except ClientDisconnect:
            logger.error(
                f"Client disconnected during request processing for {path}",
                data={"path": path, "method": method},
            )
            return JSONResponse(
                status_code=499,
                content={
                    "status": "error",
                    "message": "Client disconnected during request processing",
                    "canRetry": True,
                },
            )
        except Exception as e:
            logger.error(
                f"Unexpected error in auth middleware for {path}: {str(e)}",
                data={"path": path, "method": method, "error": str(e)},
            )
            return JSONResponse(
                {"detail": {"message": str(e), "canRetry": True}}, status_code=500
            )


def verify_token(token: str, key: str) -> dict:
    try:
        # Decode the JWT token
        claims = jwt.decode(token, key, algorithms=["HS256"])

        # Check expiration
        if "exp" in claims and datetime.utcnow().timestamp() > claims["exp"]:
            raise ValueError("Token has expired")

        return claims
    except JWTError as e:
        raise ValueError(f"Invalid Token: {e}")
