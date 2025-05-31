# helpers.py
import json
import re
import uuid
from io import BytesIO

import requests
from PIL import Image

from helpers.logger_config import logger


def get_json_from_response(content):
    """
    Extracts JSON content from a given string.

    Args:
        content (str): The string content to extract JSON from.

    Returns:
        dict or None: Extracted JSON object or None if no valid JSON is found.
    """
    # Match JSON content between triple backticks with 'json' specifier
    json_match = re.search(r"```json\s*([\s\S]*?)```", content, re.IGNORECASE)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            return None

    # Return None if no valid JSON is found
    return None


def extract_json_from_string(content):
    """
    Extracts JSON content from the given string content.

    Args:
        content (str): The string content to extract JSON from.

    Returns:
        dict or None: Extracted JSON object or None if no valid JSON is found.
    """
    if content is None:
        return None

    # First check for JSON between triple backticks
    json_match = re.search(r"```json\s*([\s\S]*?)```", content, re.IGNORECASE)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass  # Continue to next method if this fails

    # Then try to extract JSON directly with curly braces
    try:
        # Look for content that starts with { and ends with }
        direct_json_match = re.search(r"({[\s\S]*})", content)
        if direct_json_match:
            return json.loads(direct_json_match.group(1).strip())
    except json.JSONDecodeError:
        pass

    # Return None if no valid JSON is found
    return None


def get_html_string_from_content(content):
    """
    Extracts HTML content from the given string content.

    Args:
        content (str): The string content to extract HTML from.

    Returns:
        str or None: Extracted HTML string or None if no valid HTML is found.
    """
    # Match HTML content between triple backticks with 'html' specifier
    html_match = re.search(r"```html\s*([\s\S]*?)```", content, re.IGNORECASE)
    if html_match:
        return html_match.group(1).strip()

    # Check if the content starts with ```html
    if not content.strip().startswith("```html"):
        return content.strip()

    # Return None if no valid HTML is found
    return None


def download_image_to_byte_array(url):
    # Download the image
    response = requests.get(url)
    response.raise_for_status()  # Check if the download was successful

    # Open the image and convert it to byte array
    image = Image.open(BytesIO(response.content))
    img_byte_array = BytesIO()
    image.save(img_byte_array, format=image.format)
    byte_data = img_byte_array.getvalue()
    return byte_data


def get_code_from_gpt_response(content):
    """
    Extracts HTML or code snippets from the given content.

    Args:
        content (str): The string content to extract code from.

    Returns:
        str: Extracted code snippet or the original content if no match is found.
    """
    # Match HTML content between <html> tags
    html_match = re.search(r"<html[^>]*>([\s\S]*?)<\/html>", content, re.IGNORECASE)
    if html_match:
        return html_match.group(1).strip()

    # Match HTML content between <body> tags
    body_match = re.search(r"<body[^>]*>([\s\S]*?)<\/body>", content, re.IGNORECASE)
    if body_match:
        return body_match.group(1).strip()

    # Match code content between <code> tags
    code_match = re.search(r"<code[^>]*>([\s\S]*?)<\/code>", content, re.IGNORECASE)
    if code_match:
        return code_match.group(1).strip()

    # Match code content between triple backticks
    snippet_match = re.search(r"```([\s\S]*?)```", content)
    if snippet_match:
        return snippet_match.group(1).strip()

    # Return the original content if no match is found
    return content


def extract_js_code(input_string):
    # Use a regular expression to match JavaScript code enclosed in triple backticks
    match = re.search(r"```javascript\n(.*?)\n```", input_string, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def clean_postman_response(text: str) -> str:
    cleaned_text = re.sub(r"\n+", " ", text)
    cleaned_text = re.sub(r"\s+", " ", cleaned_text)
    section_headers = [
        r"API",
        r"Error Response",
        r"Request Body",
        r"Response Body",
        r"Error Codes",
        r"Headers",
        r"Attributes",
        r"Response Code",
        r"Transaction State",
        r"Document Revision History",
        r"Purpose",
        r"Status",
        r"Changes",
    ]
    headers_pattern = "|".join(section_headers)
    cleaned_text = re.sub(rf"({headers_pattern}):", r"\n\n\1:", cleaned_text)
    cleaned_text = re.sub(r"(\b\d{3}\b|\b\d+\.\b|-|\*)", r"\n• \1", cleaned_text)
    cleaned_text = re.sub(
        r"(POST|GET|DELETE|PATCH) (/v1/[^ ]+)", r"\n\n\1 \2\n", cleaned_text
    )
    key_phrases = [
        r"Request Headers",
        r"Response Headers",
        r"Request Body",
        r"Response Body",
        r"Error Response",
        r"API",
    ]
    key_phrases_pattern = "|".join(key_phrases)
    cleaned_text = re.sub(rf"({key_phrases_pattern}):", r"\n\n\1:", cleaned_text)
    cleaned_text = re.sub(r"\s([.,;:])", r"\1", cleaned_text)
    return cleaned_text.strip()


def is_valid_postman_collection(data: dict) -> bool:
    try:
        info = data.get("info")
        if not all(
            [
                isinstance(data, dict),
                isinstance(info, dict),
                isinstance(info.get("_postman_id"), str),
                isinstance(info.get("name"), str),
            ]
        ):
            return False

        items = data.get("item", [])
        if not isinstance(items, list) or len(items) == 0:
            return False

        for item in items:
            request = item.get("request", {})

            if not all(
                [
                    isinstance(item, dict),
                    isinstance(item.get("name"), str),
                    isinstance(request, dict),
                    request.get("method")
                    in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                    isinstance(request.get("url", {}).get("raw"), str),
                    isinstance(request.get("url", {}).get("protocol"), str),
                    isinstance(request.get("url", {}).get("host"), list),
                    all(
                        isinstance(h, str)
                        for h in request.get("url", {}).get("host", [])
                    ),
                    isinstance(request.get("url", {}).get("path"), list),
                    all(
                        isinstance(p, str)
                        for p in request.get("url", {}).get("path", [])
                    ),
                ]
            ):
                return False

            headers = request.get("header", [])
            if not all(
                [
                    isinstance(headers, list),
                    all(
                        isinstance(header.get("key"), str)
                        and isinstance(header.get("value"), str)
                        for header in headers
                    ),
                ]
            ):
                return False

            body = request.get("body", {})
            if body and not all(
                [
                    isinstance(body, dict),
                    body.get("mode") in ["raw", "formdata", "urlencoded", "file"],
                    body.get("mode") == "raw" and isinstance(body.get("raw"), str),
                ]
            ):
                return False

        return True

    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False


def convert_seconds_to_hms(seconds: float) -> str:
    days = int(seconds // 86400)  # 1 day = 86400 seconds
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if days > 0:
        return f"{days} days {pad_to_two_digits(hours)}:{pad_to_two_digits(minutes)}:{pad_to_two_digits(secs)}"
    return f"{pad_to_two_digits(hours)}:{pad_to_two_digits(minutes)}:{pad_to_two_digits(secs)}"


def get_user_prompt_from_base_messages(messages):
    user_messages = (msg.content for msg in messages if msg.role == "user")
    prompt = "\n".join(user_messages)
    return prompt


# Helper function to pad numbers to two digits


def pad_to_two_digits(num: int) -> str:
    return str(num).zfill(2)


def stripped_uuid4():
    return str(uuid.uuid4()).replace("-", "")


def camel_to_hyphen(camel_str):
    return "".join(["-" + c.lower() if c.isupper() else c for c in camel_str]).lstrip(
        "-"
    )


def to_camel_case(s):
    """Convert a dash-separated string to camelCase."""
    parts = s.split("-")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])
