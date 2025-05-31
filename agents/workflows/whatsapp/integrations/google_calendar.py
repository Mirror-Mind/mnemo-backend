"""
Google Calendar integration tools for WhatsApp workflow.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import tool

from helpers.logger_config import logger
from models.user_models import SessionLocal
from repository.user_repository import UserRepository


class GoogleCalendarIntegration:
    """Google Calendar API integration."""

    def __init__(self):
        """Initialize Google Calendar integration."""
        self.base_url = "https://www.googleapis.com/calendar/v3"

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
        self,
        method: str,
        endpoint: str,
        user_id: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Google Calendar API."""
        logger.debug(
            f"method: {method}, endpoint: {endpoint}, user_id: {user_id}, data: {data}, params: {params}"
        )
        access_token = self._get_access_token(user_id)
        logger.debug(f"access: token inside the make request : {access_token}")
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
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            logger.debug(
                f"response status code in calendar request: {response.status_code}"
            )
            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "Google authentication failed. Please reconnect your Google account.",
                    "code": "INVALID_TOKEN",
                }

            if not response.ok:
                logger.error(f"tool call error response: {response.json()}")
                return {
                    "success": False,
                    "error": f"Google Calendar API error: {response.status_code}",
                    "code": "CALENDAR_API_ERROR",
                }
            logger.debug(f"response response: {response.json()}")
            return {
                "success": True,
                "data": response.json() if response.content else {},
            }

        except Exception as e:
            logger.error(f"Error making Google Calendar API request: {str(e)}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "code": "REQUEST_ERROR",
            }

    def list_events(self, user_id: str, max_results: int = 10) -> Dict[str, Any]:
        """List upcoming calendar events."""
        try:
            logger.info(
                "Listing calendar events",
                data={"user_id": user_id, "max_results": max_results},
            )

            params = {
                "timeMin": datetime.now(timezone.utc).isoformat(),
                "maxResults": max_results,
                "singleEvents": "true",
                "orderBy": "startTime",
            }

            endpoint = "/calendars/primary/events"
            result = self._make_request("GET", endpoint, user_id, params=params)

            if result["success"]:
                events = result["data"].get("items", [])
                logger.info(
                    "Successfully listed calendar events",
                    data={"user_id": user_id, "count": len(events)},
                )

            return result

        except Exception as e:
            logger.error(f"Error listing calendar events: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to list calendar events: {str(e)}",
                "code": "CALENDAR_ERROR",
            }

    def create_event(
        self,
        user_id: str,
        summary: str,
        start: str,
        end: str,
        description: str = "",
        attendees: List[str] = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event."""
        try:
            logger.info(
                "Creating calendar event", data={"user_id": user_id, "summary": summary}
            )

            # Validate date formats
            try:
                datetime.fromisoformat(start.replace("Z", "+00:00"))
                datetime.fromisoformat(end.replace("Z", "+00:00"))
            except ValueError:
                return {
                    "success": False,
                    "error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS+00:00)",
                    "code": "INVALID_DATE_FORMAT",
                }

            event_data = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start, "timeZone": "UTC"},
                "end": {"dateTime": end, "timeZone": "UTC"},
            }

            if attendees:
                event_data["attendees"] = [{"email": email} for email in attendees]

            result = self._make_request(
                "POST", "/calendars/primary/events", user_id, event_data
            )

            if result["success"]:
                logger.info(
                    f"Successfully created calendar event: {result['data'].get('id')}",
                    user_id=user_id,
                )

            return result

        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to create calendar event: {str(e)}",
                "code": "CALENDAR_ERROR",
            }

    def delete_event(self, user_id: str, event_id: str) -> Dict[str, Any]:
        """Delete a calendar event."""
        try:
            logger.info(f"Deleting calendar event: {event_id}", user_id=user_id)

            result = self._make_request(
                "DELETE", f"/calendars/primary/events/{event_id}", user_id
            )

            if result["success"]:
                logger.info(
                    f"Successfully deleted calendar event: {event_id}", user_id=user_id
                )
                result["message"] = "Event successfully deleted"

            return result

        except Exception as e:
            logger.error(f"Error deleting calendar event: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to delete calendar event: {str(e)}",
                "code": "CALENDAR_ERROR",
            }


# Initialize the integration
google_calendar = GoogleCalendarIntegration()


@tool
def list_calendar_events(user_id: str, max_results: int = 10) -> str:
    """Fetch upcoming events from the user's Google Calendar."""
    try:
        logger.debug(
            f"list_calendar_events tool called, user_id: {user_id}, max_results: {max_results}"
        )
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."

        result = google_calendar.list_events(user_id, max_results)

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Google Calendar is not connected. Please connect your Google account to use calendar features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            else:
                return f"Error: {result['error']}"

        events = result["data"].get("items", [])
        if not events:
            return "No upcoming events found in your calendar."

        # Return raw events data
        return json.dumps(events)

    except Exception as e:
        logger.error(f"Error in list_calendar_events tool: {str(e)}")
        return f"Error fetching calendar events: {str(e)}"


@tool
def create_calendar_event(
    user_id: str,
    summary: str,
    start: str,
    end: str,
    description: str = "",
    attendees: List[str] = None,
) -> str:
    """Create a new event in the user's Google Calendar."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        if not summary or not summary.strip():
            return "Error: summary is required and cannot be empty."
        if not start or not start.strip():
            return "Error: start time is required and cannot be empty."
        if not end or not end.strip():
            return "Error: end time is required and cannot be empty."

        result = google_calendar.create_event(
            user_id, summary, start, end, description, attendees or []
        )

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Google Calendar is not connected. Please connect your Google account to use calendar features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            elif result["code"] == "INVALID_DATE_FORMAT":
                return "Invalid date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS+00:00)."
            else:
                return f"Error: {result['error']}"

        event_data = result["data"]
        event_id = event_data.get("id", "")
        html_link = event_data.get("htmlLink", "")

        # Return raw event data
        return json.dumps(event_data)

    except Exception as e:
        logger.error(f"Error in create_calendar_event tool: {str(e)}")
        return f"Error creating calendar event: {str(e)}"


@tool
def delete_calendar_event(user_id: str, event_id: str) -> str:
    """Delete an event from the user's Google Calendar."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        if not event_id or not event_id.strip():
            return "Error: event_id is required and cannot be empty."

        result = google_calendar.delete_event(user_id, event_id)

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Google Calendar is not connected. Please connect your Google account to use calendar features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            else:
                return f"Error: {result['error']}"

        # Return raw result data, which includes success message or error
        return json.dumps(result)

    except Exception as e:
        logger.error(f"Error in delete_calendar_event tool: {str(e)}")
        return f"Error deleting calendar event: {str(e)}"
