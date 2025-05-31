"""
WhatsApp message validation utilities.
"""

from typing import Any, Dict

from helpers.logger_config import logger


def validate_and_fix_whatsapp_message(
    message_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate and fix WhatsApp message payload to ensure it meets API requirements.

    According to WhatsApp API documentation:
    - Text message body: max 4096 characters
    - Interactive message body: max 1024 characters
    - Interactive header text: max 60 characters
    - Interactive footer text: max 60 characters
    - Interactive button text: max 20 characters
    - List section title: max 24 characters
    - List row title: max 24 characters
    - List row description: max 72 characters
    - List row id: max 200 characters
    """
    try:
        # Create a deep copy to avoid modifying the original
        validated_payload = message_payload.copy()

        message_type = validated_payload.get("type", "")

        # Validate text messages
        if message_type == "text" and "text" in validated_payload:
            body = validated_payload["text"].get("body", "")
            if len(body) > 4096:
                validated_payload["text"]["body"] = body[:4093] + "..."
                logger.warning(
                    "Text message body truncated",
                    data={
                        "original_length": len(body),
                        "truncated_length": len(validated_payload["text"]["body"]),
                    },
                )

        # Validate interactive messages
        elif message_type == "interactive" and "interactive" in validated_payload:
            interactive = validated_payload["interactive"]

            # Validate body text (max 1024 characters)
            if "body" in interactive and "text" in interactive["body"]:
                body_text = interactive["body"]["text"]
                if len(body_text) > 1024:
                    interactive["body"]["text"] = body_text[:1021] + "..."
                    logger.warning(
                        "Interactive body text truncated",
                        data={
                            "original_length": len(body_text),
                            "truncated_length": len(interactive["body"]["text"]),
                        },
                    )

            # Validate header text (max 60 characters)
            if (
                "header" in interactive
                and interactive["header"].get("type") == "text"
                and "text" in interactive["header"]
            ):
                header_text = interactive["header"]["text"]
                if len(header_text) > 60:
                    interactive["header"]["text"] = header_text[:57] + "..."
                    logger.warning(
                        "Interactive header text truncated",
                        data={
                            "original_length": len(header_text),
                            "truncated_length": len(interactive["header"]["text"]),
                        },
                    )

            # Validate footer text (max 60 characters)
            if "footer" in interactive and "text" in interactive["footer"]:
                footer_text = interactive["footer"]["text"]
                if len(footer_text) > 60:
                    interactive["footer"]["text"] = footer_text[:57] + "..."
                    logger.warning(
                        "Interactive footer text truncated",
                        data={
                            "original_length": len(footer_text),
                            "truncated_length": len(interactive["footer"]["text"]),
                        },
                    )

            # Validate action components
            if "action" in interactive:
                action = interactive["action"]

                # Validate button text (max 20 characters)
                if (
                    "button" in action
                    and isinstance(action["button"], str)
                    and len(action["button"]) > 20
                ):
                    action["button"] = action["button"][:17] + "..."
                    logger.warning(
                        "Interactive button text truncated",
                        data={
                            "original_length": len(action["button"]),
                            "truncated_length": len(action["button"]),
                        },
                    )

                # Validate buttons array (for reply buttons)
                if "buttons" in action:
                    for button in action["buttons"]:
                        if "reply" in button and "title" in button["reply"]:
                            title = button["reply"]["title"]
                            if len(title) > 20:
                                button["reply"]["title"] = title[:17] + "..."
                                logger.warning(
                                    "Reply button title truncated",
                                    data={
                                        "original_length": len(title),
                                        "truncated_length": len(
                                            button["reply"]["title"]
                                        ),
                                    },
                                )

                # Validate sections (for list messages)
                if "sections" in action:
                    for section in action["sections"]:
                        # Validate section title (max 24 characters)
                        if "title" in section and len(section["title"]) > 24:
                            section["title"] = section["title"][:21] + "..."
                            logger.warning(
                                "Section title truncated",
                                data={
                                    "original_length": len(section["title"]),
                                    "truncated_length": len(section["title"]),
                                },
                            )

                        # Validate rows
                        if "rows" in section:
                            seen_row_ids = set()
                            for i, row in enumerate(section["rows"]):
                                # Validate row title (max 24 characters)
                                if "title" in row and len(row["title"]) > 24:
                                    row["title"] = row["title"][:21] + "..."
                                    logger.warning(
                                        "Row title truncated",
                                        data={
                                            "original_length": len(row["title"]),
                                            "truncated_length": len(row["title"]),
                                        },
                                    )

                                # Validate row description (max 72 characters)
                                if (
                                    "description" in row
                                    and len(row["description"]) > 72
                                ):
                                    row["description"] = row["description"][:69] + "..."
                                    logger.warning(
                                        "Row description truncated",
                                        data={
                                            "original_length": len(row["description"]),
                                            "truncated_length": len(row["description"]),
                                        },
                                    )

                                # Validate row id (max 200 characters) and uniqueness
                                if "id" in row:
                                    original_id = str(row["id"])
                                    current_id = original_id

                                    # Ensure ID uniqueness
                                    counter = 1
                                    while current_id in seen_row_ids:
                                        suffix = f"_{counter}"
                                        # Ensure the base ID + suffix doesn't exceed 200 chars
                                        # If it does, truncate the original_id part more
                                        if len(original_id) + len(suffix) > 200:
                                            truncate_length = 200 - len(suffix)
                                            current_id = (
                                                original_id[:truncate_length] + suffix
                                            )
                                        else:
                                            current_id = original_id + suffix
                                        counter += 1

                                    if current_id != original_id:
                                        logger.warning(
                                            "Duplicate row ID found and modified.",
                                            data={
                                                "original_id": original_id,
                                                "modified_id": current_id,
                                                "row_index": i,
                                            },
                                        )
                                        row["id"] = current_id

                                    # Ensure ID length (after potential modification for uniqueness)
                                    if len(row["id"]) > 200:
                                        row["id"] = row["id"][:200]  # Max length is 200
                                        logger.warning(
                                            "Row id truncated after uniqueness fix (if any)",
                                            data={
                                                "original_length": len(original_id),
                                                "final_length": len(row["id"]),
                                            },
                                        )

                                    seen_row_ids.add(row["id"])
                                else:
                                    # If a row has no ID, assign a unique one
                                    unique_fallback_id = f"generated_row_id_{i}"
                                    counter = 1
                                    final_fallback_id = unique_fallback_id
                                    while final_fallback_id in seen_row_ids:
                                        final_fallback_id = (
                                            f"{unique_fallback_id}_{counter}"
                                        )
                                        counter += 1
                                    row["id"] = final_fallback_id
                                    seen_row_ids.add(row["id"])
                                    logger.warning(
                                        "Row missing ID, generated a unique one.",
                                        data={
                                            "generated_id": row["id"],
                                            "row_index": i,
                                        },
                                    )

        logger.info("WhatsApp message payload validated successfully")
        return validated_payload

    except Exception as e:
        logger.error(
            "Error validating WhatsApp message payload", data={"error": str(e)}
        )
        # Return original payload if validation fails
        return message_payload
