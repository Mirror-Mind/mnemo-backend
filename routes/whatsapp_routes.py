"""
WhatsApp webhook routes for handling incoming messages and verification.
"""

import hashlib
import hmac
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agents.constants.workflow_names import WHATSAPP_WORKFLOW
from agents.utils.tenant_config import get_default_orchestrator
from helpers.logger_config import logger
from models.user_models import SessionLocal, UserThread
from repository.user_repository import UserRepository
import traceback


router = APIRouter()


# Pydantic models for request validation
class WhatsAppMessage(BaseModel):
    """WhatsApp message model."""

    id: str
    from_: str = Field(alias="from")
    timestamp: str
    type: str
    text: Optional[Dict[str, str]] = None
    interactive: Optional[Dict[str, Any]] = None
    button: Optional[Dict[str, Any]] = None
    list_reply: Optional[Dict[str, Any]] = None


class WhatsAppContact(BaseModel):
    """WhatsApp contact model."""

    profile: Dict[str, str]
    wa_id: str


class WhatsAppValue(BaseModel):
    """WhatsApp webhook value model."""

    messaging_product: str
    metadata: Dict[str, Any]
    contacts: Optional[list[WhatsAppContact]] = None
    messages: Optional[list[WhatsAppMessage]] = None
    statuses: Optional[list[Dict[str, Any]]] = None


class WhatsAppChange(BaseModel):
    """WhatsApp webhook change model."""

    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    """WhatsApp webhook entry model."""

    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    """WhatsApp webhook payload model."""

    object: str
    entry: list[WhatsAppEntry]


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify WhatsApp webhook signature."""
    app_secret = os.getenv("WHATSAPP_APP_SECRET")
    if not app_secret:
        logger.warning("WHATSAPP_APP_SECRET not configured")
        return True  # Skip verification if not configured

    expected_signature = hmac.new(
        app_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    # Remove 'sha256=' prefix if present
    if signature.startswith("sha256="):
        signature = signature[7:]

    return hmac.compare_digest(expected_signature, signature)


async def process_whatsapp_message_background(
    message: WhatsAppMessage, contact: WhatsAppContact, phone_number_id: str
):
    """Background task to process WhatsApp message."""
    db_session = None  # Initialize db_session to ensure it's defined
    try:
        logger.info(
            "Processing WhatsApp message in background",
            data={
                "message_id": message.id,
                "from_number": message.from_,
                "phone_number_id": phone_number_id,
            },
        )

        # Send thinking emoji reaction to show processing has started
        await send_whatsapp_reaction(message.from_, message.id, "🤔")

        # Extract message content
        message_content = ""

        if message.text:
            message_content = message.text.get("body", "")
        elif message.interactive:
            if message.interactive.get("type") == "button_reply":
                message_content = message.interactive.get("button_reply", {}).get(
                    "title", ""
                )
            elif message.interactive.get("type") == "list_reply":
                message_content = message.interactive.get("list_reply", {}).get(
                    "title", ""
                )
        elif message.button:
            message_content = message.button.get("text", "")
        elif message.list_reply:
            message_content = message.list_reply.get("title", "")

        if not message_content:
            logger.warning("No message content found", data={"message_id": message.id})
            return

        # Initialize UserRepository
        db_session = SessionLocal()
        user_repo = UserRepository(db_session)

        # Fetch user by phone number
        logger.info("Fetching user by phone number", data={"from": message.from_})
        user = user_repo.get_user_by_phone_number("+" + message.from_)

        if not user:
            logger.warning(
                "User not found by phone number. Instructing to sign up.",
                data={"phone_number": message.from_, "message_id": message.id},
            )
            signup_message_payload = {
                "messaging_product": "whatsapp",
                "to": message.from_,
                "type": "text",
                "text": {
                    "body": "Please sign up at orbia.ishaan812.com to access my services."
                },
            }
            await send_whatsapp_message(signup_message_payload, message.id)
            await send_whatsapp_reaction(message.from_, message.id, "❌")
            logger.info(
                "Sign-up instruction sent to user.",
                data={"phone_number": message.from_},
            )
            return  # Stop processing if user not found

        user_id = user.id
        logger.info(
            "Existing user found by phone number",
            data={"user_id": user_id, "phone_number": message.from_},
        )
        user_profile_name = user.name or contact.profile.get("name", "User")

        workflow_orchestrator = get_default_orchestrator()
        initial_state = {
            "user_id": user_id,
            "phone_number": message.from_,
            "whatsapp_message_id": message.id,
        }
        user_thread = user_repo.get_user_thread(user_id=user_id)
        if not user_thread:
            logger.info("No user thread found, creating new one")
            threadId, result, type, _ = workflow_orchestrator.start(
                workflow_name=WHATSAPP_WORKFLOW,
                message_dict={
                    "content": message_content,
                },
                **initial_state,
            )
            user_thread = UserThread(
                id=threadId,
                userId=user_id,
                threadId=threadId,
                createdAt=datetime.now(),
                updatedAt=datetime.now(),
            )
            db_session.add(user_thread)
            db_session.commit()
            logger.info(
                "New user thread created",
                data={"user_id": user_id, "thread_id": threadId},
            )
        initial_state["session_id"] = user_thread.threadId
        result, type, interrupt_message = workflow_orchestrator.chat(
            workflow_name=WHATSAPP_WORKFLOW,
            thread_id=user_thread.threadId,
            message_dict={
                "content": message_content,
            },
            **initial_state,
        )
        
        # Debug logging to understand result structure
        logger.debug(
            "Workflow result received",
            data={
                "user_id": user_id,
                "has_result": bool(result),
                "has_response_content": bool(result and result.get("response_content")),
                "error_value": result.get("error") if result else None,
                "error_type": type(result.get("error")) if result and result.get("error") is not None else None,
            }
        )
        # Format response for WhatsApp
        if (result and 
            result.get("response_content") and 
            (result.get("error") is None or result.get("error") == "")):
            # Success: we have response_content and no error (or error is None/empty)
            whatsapp_response = result.get("response_content")
            whatsapp_response["to"] = message.from_
            await send_whatsapp_message(whatsapp_response, message.id)
            await send_whatsapp_reaction(message.from_, message.id, "✅")
            logger.info(
                "Successfully processed and sent WhatsApp response",
                data={"message_id": message.id, "session_id": result.get("session_id")},
            )
        else:
            error_msg = result.get("error") if result else "No response generated"
            # Log the actual error instead of call stack
            logger.error(
                "Failed to process WhatsApp message",
                data={"message_id": message.id, "error": error_msg, "result": result},
            )
            
            # Check if this is a quota-related error
            is_quota_error = False
            user_friendly_message = "Sorry, I encountered an error processing your message. Please try again later."
            
            if error_msg and isinstance(error_msg, str):
                error_lower = error_msg.lower()
                if any(keyword in error_lower for keyword in ["quota", "rate limit", "exceeded", "429"]):
                    is_quota_error = True
                    user_friendly_message = "I'm currently experiencing high usage and have reached my daily limit. Please try again in a few hours. Thank you for your patience! 🙏"
                elif "500" in error_msg:
                    user_friendly_message = "I'm experiencing some technical difficulties. Please try again in a few minutes."
                elif "timeout" in error_lower or "connection" in error_lower:
                    user_friendly_message = "I'm having trouble connecting to my services. Please try again shortly."
            
            error_response = {
                "messaging_product": "whatsapp",
                "to": message.from_,
                "type": "text",
                "text": {
                    "body": user_friendly_message
                },
            }
            await send_whatsapp_message(error_response, message.id)
            
            # Use different reaction emoji for quota errors
            reaction_emoji = "⏳" if is_quota_error else "❌"
            await send_whatsapp_reaction(message.from_, message.id, reaction_emoji)

    except Exception as e:
        logger.error(
            "Error in background message processing",
            data={"message_id": message.id, "error": str(e)},
        )
        # Send error message to user
        try:
            # Determine user-friendly message based on error type
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["quota", "rate limit", "exceeded", "429"]):
                user_message = "I'm currently experiencing high usage and have reached my daily limit. Please try again in a few hours. Thank you for your patience! 🙏"
                reaction_emoji = "⏳"
            elif "timeout" in error_str or "connection" in error_str:
                user_message = "I'm having trouble connecting to my services. Please try again shortly."
                reaction_emoji = "❌"
            elif "500" in error_str or "internal server error" in error_str:
                user_message = "I'm experiencing some technical difficulties. Please try again in a few minutes."
                reaction_emoji = "❌"
            else:
                user_message = "Sorry, I encountered an unexpected error. Please try again later."
                reaction_emoji = "❌"
                
            error_response = {
                "messaging_product": "whatsapp",
                "to": message.from_,
                "type": "text",
                "text": {
                    "body": user_message
                },
            }
            await send_whatsapp_message(error_response, message.id)
            await send_whatsapp_reaction(message.from_, message.id, reaction_emoji)
        except Exception as send_error:
            logger.error(
                "Failed to send error message to user", data={"error": str(send_error)}
            )
            # Try to send error reaction even if message sending failed
            try:
                await send_whatsapp_reaction(message.from_, message.id, "❌")
            except Exception as reaction_error:
                logger.error(
                    "Failed to send error reaction", data={"error": str(reaction_error)}
                )
    finally:
        if db_session:
            db_session.close()


async def send_whatsapp_reaction(to: str, message_id: str, emoji: str) -> bool:
    """Send a reaction to a WhatsApp message."""
    import httpx

    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not access_token or not phone_number_id:
        logger.error("WhatsApp credentials not configured for reactions")
        return False

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Prepare the reaction payload
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "reaction",
        "reaction": {"message_id": message_id, "emoji": emoji},
    }

    action_type = "Removing" if emoji == "" else "Sending"
    logger.info(f"{action_type} WhatsApp reaction", data={"payload": payload})

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)

            response.raise_for_status()
            response_data = response.json()
            logger.info(
                f"WhatsApp reaction {emoji if emoji else 'removed'} successfully",
                data={"response_data": response_data},
            )
            return True

    except httpx.HTTPStatusError as e:
        logger.error(
            "WhatsApp API HTTP error for reaction",
            data={
                "status_code": e.response.status_code,
                "response_text": e.response.text,
                "request_payload": payload,
            },
        )
        return False
    except Exception as e:
        logger.error("Failed to send WhatsApp reaction", data={"error": str(e)})
        return False


async def send_whatsapp_message(
    message_payload: Dict[str, Any], message_id: Optional[str] = None
):
    """Send message to WhatsApp API."""
    import httpx

    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not access_token or not phone_number_id:
        logger.error("WhatsApp credentials not configured")
        return

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    if message_id:
        message_payload["context"] = {"message_id": message_id}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=message_payload, headers=headers)

            response.raise_for_status()
            response_data = response.json()
            logger.info(
                "Successfully sent WhatsApp message",
                data={"response_data": response_data},
            )

    except httpx.HTTPStatusError as e:
        logger.error(
            "WhatsApp API HTTP error",
            data={
                "status_code": e.response.status_code,
                "response_text": e.response.text,
                "request_payload": message_payload,
                "message_id": message_id,
            },
        )
    except Exception as e:
        logger.error("Failed to send WhatsApp message", data={"error": str(e)})


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Verify WhatsApp webhook."""
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    if not verify_token:
        raise HTTPException(
            status_code=500, detail="WHATSAPP_VERIFY_TOKEN not configured"
        )

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return int(challenge)
    else:
        logger.warning("WhatsApp webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def handle_webhook(
    request: Request, background_tasks: BackgroundTasks, payload: WhatsAppWebhookPayload
):
    """Handle incoming WhatsApp webhook."""
    try:
        # Verify signature
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

        logger.info("Received WhatsApp webhook", data={"payload": payload.model_dump()})

        # Process each entry
        for _entry_idx, entry in enumerate(payload.entry):
            for _change_idx, change in enumerate(entry.changes):
                if change.field == "messages":
                    value = change.value
                    # Process messages
                    if value.messages:
                        for _msg_idx, message in enumerate(value.messages):
                            # Find corresponding contact
                            contact = None
                            if value.contacts:
                                for c in value.contacts:
                                    if c.wa_id == message.from_:
                                        contact = c
                                        break

                            if not contact:
                                logger.warning(
                                    "No contact found for message",
                                    data={"message_id": message.id},
                                )
                                continue

                            # Add background task to process message
                            background_tasks.add_task(
                                process_whatsapp_message_background,
                                message,
                                contact,
                                value.metadata.get("phone_number_id", ""),
                            )

                    # Log status updates
                    if value.statuses:
                        for _status_idx, status in enumerate(value.statuses):
                            logger.info(
                                "WhatsApp message status update",
                                data={"status": status},
                            )

        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        logger.error("Error handling WhatsApp webhook", data={"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


# @router.post("/send-message")


@router.get("/health")
async def health_check():
    """Health check endpoint for WhatsApp webhook."""
    return {"status": "healthy", "service": "whatsapp-webhook"}
