import functools
import os
from typing import Any, Callable, Dict, Optional

from helpers.langfuse_config import get_langfuse_client, is_langfuse_enabled
from helpers.logger_config import logger

# Initialize Langfuse client with proper environment variable handling
langfuse = get_langfuse_client(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL"),
    debug=True,
)


def with_langfuse_tracing(
    trace_name: str,
    model_name: str,
    session_id: str,
    user_id: str,
    input_data: Any,
    model_params: Dict[str, Any],
    api_call: Callable[..., Any],
    tags: Optional[list[str]] = None,
    **kwargs: Any,
) -> Callable[..., Any]:
    """
    Decorator to trace an API call with Langfuse using modern @observe pattern.

    Args:
        trace_name: Name of the trace.
        model_name: Name of the model being used.
        session_id: Session ID for the trace.
        user_id: User ID for the trace.
        input_data: Input data for the API call.
        model_params: Parameters for the model.
        api_call: The actual API call function to be traced.
        tags: Optional list of tags for the trace.
        **kwargs: Additional metadata for the trace.
    """

    # If Langfuse is disabled, just call the API directly
    if not is_langfuse_enabled():
        if api_call:
            return api_call()
        return lambda func: func

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        try:
            from langfuse.decorators import langfuse_context, observe

            @observe(name=trace_name)
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs_inner: Any) -> Any:
                # Update trace with metadata
                langfuse_context.update_current_trace(
                    name=trace_name,
                    session_id=session_id,
                    user_id=user_id,
                    metadata={
                        **kwargs,
                        "model_name": model_name,
                        "model_params": model_params,
                    },
                    tags=tags,
                )

                # Update current observation with input data
                langfuse_context.update_current_observation(
                    input=input_data,
                    metadata={"model_name": model_name, **model_params},
                )

                try:
                    result = func(*args, **kwargs_inner)
                    # Update observation with output
                    langfuse_context.update_current_observation(output=result)
                    return result
                except Exception as e:
                    logger.error(f"Error in API call during Langfuse tracing: {str(e)}")
                    langfuse_context.update_current_observation(
                        output={"error": str(e)}, level="ERROR"
                    )
                    raise

            return wrapper
        except ImportError:
            logger.warning("Langfuse decorators not available, running without tracing")
            return func

    if api_call:

        @decorator
        def decorated_api_call():
            return api_call()

        return decorated_api_call()
    return decorator


def with_langfuse_image_tracing(
    trace_name: str,
    model_name: str,
    session_id: str,
    user_id: str,
    input_data: Any,
    model_params: Dict[str, Any],
    api_call: Callable[..., Any],
    tags: Optional[list[str]] = None,
    **kwargs: Any,
) -> Any:
    """
    Wrap an image generation API call with Langfuse tracing using modern approach.

    Args:
        trace_name: Name for the trace (e.g., "image_generation")
        model_name: Name of the model being used (e.g., "replicate/model")
        session_id: Session ID
        user_id: User ID for tracking
        input_data: Input data to the model
        model_params: Model parameters
        api_call: Function that makes the actual API call
        tags: Optional list of tags for the trace.
        **kwargs: Additional metadata for the trace.

    Returns:
        The result of the API call
    """
    # If Langfuse is disabled, just call the API directly
    if not is_langfuse_enabled():
        return api_call()

    try:
        from langfuse.decorators import langfuse_context, observe

        @observe(name=trace_name)
        def traced_api_call():
            # Update trace with metadata
            langfuse_context.update_current_trace(
                name=trace_name,
                session_id=session_id,
                user_id=user_id,
                metadata={**kwargs, "model_name": model_name},
                tags=tags,
            )

            # Update current observation with input data
            langfuse_context.update_current_observation(
                name="image_generation_call",
                input=input_data,
                metadata={"model_name": model_name, **model_params},
            )

            try:
                output = api_call()
                langfuse_context.update_current_observation(output=output)
                return output
            except Exception as e:
                logger.error(
                    f"Error in API call during Langfuse image tracing: {str(e)}"
                )
                langfuse_context.update_current_observation(
                    output={"error": str(e)}, level="ERROR"
                )
                raise

        return traced_api_call()
    except ImportError:
        logger.warning("Langfuse decorators not available, running without tracing")
        return api_call()


def with_langfuse_event_tracing(
    trace_name: str,
    session_id: str,
    user_id: str,
    event_name: str,
    input_data: Any,
    output_data: Any,
    model_params: Dict[str, Any],
    tags: Optional[list[str]] = None,
    **kwargs: Any,
) -> Callable[..., Any]:
    """
    Decorator to trace an event with Langfuse using modern @observe pattern.

    Args:
        trace_name: Name of the trace.
        session_id: Session ID for the trace.
        user_id: User ID for the trace.
        event_name: Name of the event.
        input_data: Input data for the event.
        output_data: Output data for the event.
        model_params: Parameters (might be generic event params).
        tags: Optional list of tags for the trace.
        **kwargs: Additional metadata for the trace.
    """

    # If Langfuse is disabled, return a no-op decorator
    if not is_langfuse_enabled():
        return lambda func: func

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        try:
            from langfuse.decorators import langfuse_context, observe

            @observe(name=event_name)
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs_inner: Any) -> Any:
                # Update trace with metadata
                langfuse_context.update_current_trace(
                    name=trace_name,
                    session_id=session_id,
                    user_id=user_id,
                    metadata=kwargs,
                    tags=tags,
                )

                # Update current observation with event data
                langfuse_context.update_current_observation(
                    name=event_name,
                    input=input_data,
                    metadata={**kwargs, **model_params},
                )

                try:
                    result = func(*args, **kwargs_inner)
                    langfuse_context.update_current_observation(output=result)
                    return result
                except Exception as e:
                    logger.error(f"Error in event during Langfuse tracing: {str(e)}")
                    langfuse_context.update_current_observation(
                        output={"error": str(e)}, level="ERROR"
                    )
                    raise

            return wrapper
        except ImportError:
            logger.warning("Langfuse decorators not available, running without tracing")
            return func

    return decorator


# Additional utility functions for modern Langfuse usage


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID from Langfuse context."""
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse.decorators import langfuse_context

        return langfuse_context.get_current_trace_id()
    except Exception as e:
        logger.warning(f"Could not get current trace ID: {str(e)}")
        return None


def get_current_observation_id() -> Optional[str]:
    """Get the current observation ID from Langfuse context."""
    if not is_langfuse_enabled():
        return None

    try:
        from langfuse.decorators import langfuse_context

        return langfuse_context.get_current_observation_id()
    except Exception as e:
        logger.warning(f"Could not get current observation ID: {str(e)}")
        return None


def score_current_trace(name: str, value: float, comment: Optional[str] = None) -> None:
    """Score the current trace."""
    if not is_langfuse_enabled():
        return

    try:
        from langfuse.decorators import langfuse_context

        langfuse_context.score_current_trace(name=name, value=value, comment=comment)
    except Exception as e:
        logger.warning(f"Could not score current trace: {str(e)}")


def score_current_observation(
    name: str, value: float, comment: Optional[str] = None
) -> None:
    """Score the current observation."""
    if not is_langfuse_enabled():
        return

    try:
        from langfuse.decorators import langfuse_context

        langfuse_context.score_current_observation(
            name=name, value=value, comment=comment
        )
    except Exception as e:
        logger.warning(f"Could not score current observation: {str(e)}")


def flush_langfuse() -> None:
    """Flush Langfuse to ensure all traces are sent."""
    if not is_langfuse_enabled():
        return

    try:
        from langfuse.decorators import langfuse_context

        langfuse_context.flush()
    except Exception as e:
        logger.warning(f"Could not flush Langfuse: {str(e)}")
