import os

from constants.exceptions import Exceptions
from helpers.langfuse_config import get_langfuse_client, is_langfuse_enabled
from helpers.logger_config import logger


def get_prompt_from_langfuse(prompt_key: str, **kwargs) -> str | None:
    # Check if Langfuse prompts are explicitly disabled or if Langfuse is disabled
    if (
        os.getenv("LANGFUSE_PROMPTS_FETCH_ENABLED") == "false"
        or not is_langfuse_enabled()
    ):
        return get_prompt_from_local(prompt_key, **kwargs)

    LANGFUSE_PROMPT_CACHE_TTL_IN_SEC = int(
        os.getenv("LANGFUSE_PROMPT_CACHE_TTL_IN_SEC", "60")
    )
    try:
        langfuse = get_langfuse_client()
        if not langfuse:
            logger.warning(
                "Langfuse client not available, falling back to local prompts"
            )
            return get_prompt_from_local(prompt_key, **kwargs)

        prompt_response = langfuse.get_prompt(
            prompt_key, cache_ttl_seconds=LANGFUSE_PROMPT_CACHE_TTL_IN_SEC
        )
        prompt = prompt_response.compile(**kwargs)
        logger.info(f"Prompt fetched from Langfuse: {prompt_key}")
        return prompt
    except Exception as e:
        logger.warning(f"Failed to fetch prompt from Langfuse: {e}")
        prompt_template = get_prompt_from_local(prompt_key, **kwargs)
        if prompt_template:
            for key, value in kwargs.items():
                word = "{{" + key + "}}"
                prompt_template = prompt_template.replace(word, str(value))
            return prompt_template
        raise Exceptions.general_exception(500, f"Prompt not found: {prompt_key}")


def get_prompt_from_local(prompt_key: str, **kwargs) -> str | None:
    from constants.prompt_map import PROMPT_MAP_DYNAMIC, PROMPT_MAP_STATIC

    if PROMPT_MAP_DYNAMIC.get(prompt_key):
        return PROMPT_MAP_DYNAMIC[prompt_key](**kwargs)
    return PROMPT_MAP_STATIC.get(prompt_key, None)
