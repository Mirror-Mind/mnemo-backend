import os
from typing import Optional

from helpers.logger_config import logger


def is_langfuse_enabled() -> bool:
    """
    Check if Langfuse is enabled via environment variable.

    Returns:
        bool: True if Langfuse is enabled, False otherwise
    """
    enabled = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"

    if enabled:
        # Also check if required environment variables are set
        required_vars = [
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_BASE_URL",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.warning(
                f"Langfuse is enabled but missing required environment variables: {missing_vars}. "
                "Disabling Langfuse."
            )
            return False

    return enabled


def get_langfuse_callback_handler(*args, **kwargs) -> Optional[object]:
    """
    Get Langfuse CallbackHandler if enabled, otherwise return None.

    Args:
        *args: Arguments to pass to CallbackHandler
        **kwargs: Keyword arguments to pass to CallbackHandler

    Returns:
        CallbackHandler instance if enabled, None otherwise
    """
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Failed to create Langfuse CallbackHandler: {e}")
        return None


def get_langfuse_client(*args, **kwargs) -> Optional[object]:
    """
    Get Langfuse client if enabled, otherwise return None.

    Args:
        *args: Arguments to pass to Langfuse client
        **kwargs: Keyword arguments to pass to Langfuse client

    Returns:
        Langfuse client instance if enabled, None otherwise
    """
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse import Langfuse

        return Langfuse(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Failed to create Langfuse client: {e}")
        return None
