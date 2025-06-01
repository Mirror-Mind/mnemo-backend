"""
WhatsApp integration for sending messages.
"""

import os
from typing import Dict, Any

import requests
from helpers.logger_config import logger


async def send_whatsapp_message(message_payload: Dict[str, Any]) -> bool:
    """
    Send a WhatsApp message using the WhatsApp Business API.
    
    Args:
        message_payload: Dictionary containing the message details
            {
                "to": str,  # Recipient's phone number
                "type": str,  # Message type (e.g., "text")
                "text": {  # Message content
                    "body": str
                }
            }
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        # Get WhatsApp API credentials from environment
        whatsapp_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        whatsapp_phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        
        if not whatsapp_token or not whatsapp_phone_number_id:
            logger.error("WhatsApp credentials not configured")
            return False

        # Prepare the API request
        url = f"https://graph.facebook.com/v17.0/{whatsapp_phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {whatsapp_token}",
            "Content-Type": "application/json"
        }
        
        # Add messaging product to payload
        # Check if the message is text and needs to be chunked
        if (
            message_payload.get("type") == "text"
            and "text" in message_payload
            and isinstance(message_payload["text"], dict)
            and "body" in message_payload["text"]
            and isinstance(message_payload["text"]["body"], str)
            and len(message_payload["text"]["body"]) > 3800
        ):
            text_body = message_payload["text"]["body"]
            chunks = [text_body[i:i+3800] for i in range(0, len(text_body), 3800)]
            success = True
            for chunk in chunks:
                chunk_payload = {
                    "messaging_product": "whatsapp",
                    **{**message_payload, "text": {"body": chunk}}
                }
                response = requests.post(url, headers=headers, json=chunk_payload)
                if not response.ok:
                    logger.error(
                    f"Failed to send WhatsApp message chunk: {response.status_code} - {response.text}",
                    data={"payload": chunk_payload}
                    )
                    success = False
            return success
        else:
            payload = {
            "messaging_product": "whatsapp",
            **message_payload
            }

        # Send the request
        response = requests.post(url, headers=headers, json=payload)
        
        if not response.ok:
            logger.error(
                f"Failed to send WhatsApp message: {response.status_code} - {response.text}",
                data={"payload": payload}
            )
            return False

        logger.info(
            "WhatsApp message sent successfully",
            data={"to": message_payload["to"]}
        )
        return True

    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}")
        return False 