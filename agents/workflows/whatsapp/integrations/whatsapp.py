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