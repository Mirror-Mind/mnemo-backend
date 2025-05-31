"""
Gmail integration tools for WhatsApp workflow.
"""

import base64
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import tool

from helpers.logger_config import logger
from models.user_models import SessionLocal
from repository.user_repository import UserRepository


class GmailIntegration:
    """Gmail API integration."""

    def __init__(self):
        """Initialize Gmail integration."""
        self.base_url = "https://gmail.googleapis.com/gmail/v1"

    def _get_access_token(self, user_id: str) -> Optional[str]:
        """Get Google access token for user."""
        try:
            db = SessionLocal()
            repo = UserRepository(db)
            token = repo.get_google_access_token(user_id)
            db.close()
            return token
        except Exception as e:
            logger.error(
                f"Error getting Google access token: {str(e)}", user_id=user_id
            )
            return None

    def _make_request(
        self, method: str, endpoint: str, user_id: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Gmail API."""
        access_token = self._get_access_token(user_id)
        if not access_token:
            return {
                "success": False,
                "error": "No Google account connected",
                "code": "NO_GOOGLE_ACCOUNT",
            }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "Google authentication failed. Please reconnect your Google account.",
                    "code": "INVALID_TOKEN",
                }

            if not response.ok:
                return {
                    "success": False,
                    "error": f"Gmail API error: {response.status_code}",
                    "code": "GMAIL_API_ERROR",
                }

            return {
                "success": True,
                "data": response.json() if response.content else {},
            }

        except Exception as e:
            logger.error(f"Error making Gmail API request: {str(e)}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "code": "REQUEST_ERROR",
            }

    def list_messages(
        self,
        user_id: str,
        max_results: int = 10,
        query: str = "",
        label_ids: List[str] = None,
    ) -> Dict[str, Any]:
        """List Gmail messages."""
        try:
            logger.info(
                "Listing Gmail messages",
                data={"user_id": user_id, "max_results": max_results},
            )

            params = {"maxResults": max_results}
            if query:
                params["q"] = query
            if label_ids:
                params["labelIds"] = label_ids

            endpoint = "/users/me/messages?" + "&".join(
                [f"{k}={v}" for k, v in params.items()]
            )
            result = self._make_request("GET", endpoint, user_id)

            if not result["success"]:
                return result

            messages = result["data"].get("messages", [])

            # Get basic message details for each message (headers only, no body)
            detailed_messages = []
            for message in messages[:max_results]:  # Limit to avoid too many API calls
                message_detail = self.get_message_headers(user_id, message["id"])
                if message_detail["success"]:
                    detailed_messages.append(message_detail["data"])

            result["data"]["messages"] = detailed_messages
            logger.info(
                "Successfully listed Gmail messages",
                data={"user_id": user_id, "count": len(detailed_messages)},
            )

            return result

        except Exception as e:
            logger.error(f"Error listing Gmail messages: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to list Gmail messages: {str(e)}",
                "code": "GMAIL_ERROR",
            }

    def get_message_headers(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """Get Gmail message headers and snippet (faster than full message)."""
        try:
            logger.info(
                "Getting Gmail message headers",
                user_id=user_id,
                data={"message_id": message_id},
            )

            # Use format=metadata to get only headers and snippet, not body
            result = self._make_request(
                "GET", f"/users/me/messages/{message_id}?format=metadata", user_id
            )

            if result["success"]:
                # Extract useful information from the message
                message_data = result["data"]
                headers = message_data.get("payload", {}).get("headers", [])

                # Extract common headers
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"), ""
                )
                from_email = next(
                    (h["value"] for h in headers if h["name"] == "From"), ""
                )
                to_email = next((h["value"] for h in headers if h["name"] == "To"), "")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "")

                result["data"] = {
                    "id": message_data.get("id"),
                    "threadId": message_data.get("threadId"),
                    "subject": subject,
                    "from": from_email,
                    "to": to_email,
                    "date": date,
                    "body": "",  # No body for listing
                    "snippet": message_data.get("snippet", ""),
                }

                logger.info(
                    "Successfully retrieved Gmail message headers",
                    user_id=user_id,
                    data={"message_id": message_id},
                )

            return result

        except Exception as e:
            logger.error(
                "Error getting Gmail message headers",
                user_id=user_id,
                data={"error": str(e)},
            )
            return {
                "success": False,
                "error": f"Failed to get Gmail message headers: {str(e)}",
                "code": "GMAIL_ERROR",
            }

    def get_message(self, user_id: str, message_id: str) -> Dict[str, Any]:
        """Get a specific Gmail message."""
        try:
            logger.info(
                "Getting Gmail message",
                user_id=user_id,
                data={"message_id": message_id},
            )

            result = self._make_request(
                "GET", f"/users/me/messages/{message_id}", user_id
            )

            if result["success"]:
                # Extract useful information from the message
                message_data = result["data"]
                headers = message_data.get("payload", {}).get("headers", [])

                # Extract common headers
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"), ""
                )
                from_email = next(
                    (h["value"] for h in headers if h["name"] == "From"), ""
                )
                to_email = next((h["value"] for h in headers if h["name"] == "To"), "")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "")

                # Extract body
                body = self._extract_message_body(message_data.get("payload", {}))

                result["data"] = {
                    "id": message_data.get("id"),
                    "threadId": message_data.get("threadId"),
                    "subject": subject,
                    "from": from_email,
                    "to": to_email,
                    "date": date,
                    "body": body,
                    "snippet": message_data.get("snippet", ""),
                }

                logger.info(
                    "Successfully retrieved Gmail message",
                    user_id=user_id,
                    data={"message_id": message_id},
                )

            return result

        except Exception as e:
            logger.error(
                "Error getting Gmail message", user_id=user_id, data={"error": str(e)}
            )
            return {
                "success": False,
                "error": f"Failed to get Gmail message: {str(e)}",
                "code": "GMAIL_ERROR",
            }

    def send_message(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
    ) -> Dict[str, Any]:
        """Send a Gmail message."""
        try:
            logger.info(
                "Sending Gmail message",
                data={"user_id": user_id, "to": to, "subject": subject},
            )

            # Always append "Sent from Orbia" to the body
            enhanced_body = f"{body}\n\nSent from Orbia"

            # Construct email
            email_lines = []
            email_lines.append(f"To: {to}")
            if cc:
                email_lines.append(f"Cc: {cc}")
            if bcc:
                email_lines.append(f"Bcc: {bcc}")
            email_lines.append(f"Subject: {subject}")
            email_lines.append("")
            email_lines.append(enhanced_body)

            email = "\r\n".join(email_lines).encode("utf-8")
            base64_email = base64.urlsafe_b64encode(email).decode("utf-8")

            message_data = {"raw": base64_email}

            result = self._make_request(
                "POST", "/users/me/messages/send", user_id, message_data
            )

            if result["success"]:
                logger.info(
                    "Successfully sent Gmail message",
                    data={"user_id": user_id, "message_id": result["data"].get("id")},
                )

            return result

        except Exception as e:
            logger.error(f"Error sending Gmail message: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to send Gmail message: {str(e)}",
                "code": "GMAIL_ERROR",
            }

    def _extract_message_body(self, payload: Dict) -> str:
        """Extract message body from Gmail payload."""
        try:
            # Check if body is directly available
            if payload.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

            # Check parts for text/plain content
            parts = payload.get("parts", [])
            for part in parts:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get(
                    "data"
                ):
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )

            # Fallback to snippet if no body found
            return ""

        except Exception as e:
            logger.error("Error extracting message body", data={"error": str(e)})
            return ""


gmail = GmailIntegration()


@tool
def list_gmail_messages(
    user_id: str, max_results: int = 10, query: str = "", label_ids: List[str] = None
) -> str:
    """Lists emails from the user's Gmail inbox."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."

        result = gmail.list_messages(user_id, max_results, query, label_ids or [])

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Gmail account is not connected. Please connect your Google account to use Gmail features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            else:
                return f"Error: {result['error']}"

        messages = result["data"].get("messages", [])
        if not messages:
            return "No emails found in your inbox."

        # Format messages for display
        formatted_messages = []
        for message in messages:
            subject = message.get("subject", "No subject")
            from_email = message.get("from", "Unknown sender")
            date = message.get("date", "No date")
            snippet = message.get("snippet", "")

            formatted_messages.append(
                f"• {subject}\n  From: {from_email}\n  Date: {date}\n  Preview: {snippet[:100]}..."
            )

        return "Your recent emails:\n\n" + "\n\n".join(formatted_messages)

    except Exception as e:
        logger.error("Error in list_gmail_messages tool", data={"error": str(e)})
        return f"Error fetching emails: {str(e)}"


@tool
def read_gmail_message(user_id: str, message_id: str) -> str:
    """Reads a specific email message from Gmail."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        if not message_id or not message_id.strip():
            return "Error: message_id is required and cannot be empty."

        result = gmail.get_message(user_id, message_id)

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Gmail account is not connected. Please connect your Google account to use Gmail features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            else:
                return f"Error: {result['error']}"

        message = result["data"]
        subject = message.get("subject", "No subject")
        from_email = message.get("from", "Unknown sender")
        to_email = message.get("to", "")
        date = message.get("date", "No date")
        body = message.get("body", "No content available")

        formatted_message = f"""
Email Details:
Subject: {subject}
From: {from_email}
To: {to_email}
Date: {date}

Content:
{body}
        """.strip()

        return formatted_message

    except Exception as e:
        logger.error("Error in read_gmail_message tool", data={"error": str(e)})
        return f"Error reading email: {str(e)}"


@tool
def send_gmail_message(
    user_id: str, to: str, subject: str, body: str, cc: str = "", bcc: str = ""
) -> str:
    """Sends an email using Gmail."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        if not to or not to.strip():
            return "Error: to email is required and cannot be empty."
        if not subject or not subject.strip():
            return "Error: subject is required and cannot be empty."
        if not body or not body.strip():
            return "Error: body is required and cannot be empty."

        result = gmail.send_message(user_id, to, subject, body, cc, bcc)

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Gmail account is not connected. Please connect your Google account to use Gmail features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            else:
                return f"Error: {result['error']}"

        message_data = result["data"]
        message_id = message_data.get("id", "")

        return f"Successfully sent email to {to} with subject '{subject}'. Message ID: {message_id}"

    except Exception as e:
        logger.error("Error in send_gmail_message tool", data={"error": str(e)})
        return f"Error sending email: {str(e)}"
