"""
Google Docs integration tools for WhatsApp workflow.
"""

from typing import Any, Dict, Optional

import requests
from langchain_core.tools import tool

from helpers.logger_config import logger
from models.user_models import SessionLocal
from repository.user_repository import UserRepository


class GoogleDocsIntegration:
    """Google Docs API integration."""

    def __init__(self):
        """Initialize Google Docs integration."""
        self.drive_base_url = "https://www.googleapis.com/drive/v3"
        self.docs_base_url = "https://docs.googleapis.com/v1"

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
        """Make authenticated request to Google API."""
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

        try:
            if method.upper() == "GET":
                response = requests.get(endpoint, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(endpoint, headers=headers, json=data)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "Google authentication failed. Please reconnect your Google account.",
                    "code": "INVALID_TOKEN",
                }

            if response.status_code == 404:
                return {
                    "success": False,
                    "error": "Document not found",
                    "code": "DOC_NOT_FOUND",
                }

            if not response.ok:
                return {
                    "success": False,
                    "error": f"Google API error: {response.status_code}",
                    "code": "DOCS_API_ERROR",
                }

            return {
                "success": True,
                "data": response.json() if response.content else {},
            }

        except Exception as e:
            logger.error(f"Error making Google API request: {str(e)}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "code": "REQUEST_ERROR",
            }

    def list_documents(self, user_id: str, max_results: int = 10) -> Dict[str, Any]:
        """List Google Docs from Drive."""
        try:
            logger.info(
                "Listing Google Docs",
                data={"user_id": user_id, "max_results": max_results},
            )

            params = {
                "q": "mimeType='application/vnd.google-apps.document'",
                "fields": "files(id,name,createdTime,modifiedTime,webViewLink)",
                "orderBy": "modifiedTime desc",
                "pageSize": max_results,
            }

            endpoint = f"{self.drive_base_url}/files?" + "&".join(
                [f"{k}={v}" for k, v in params.items()]
            )
            result = self._make_request("GET", endpoint, user_id)

            if result["success"]:
                files = result["data"].get("files", [])
                logger.info(
                    "Successfully listed Google Docs",
                    data={"user_id": user_id, "count": len(files)},
                )

            return result

        except Exception as e:
            logger.error(f"Error listing Google Docs: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to list Google Docs: {str(e)}",
                "code": "DOCS_ERROR",
            }

    def get_document_content(self, user_id: str, document_id: str) -> Dict[str, Any]:
        """Get content of a specific Google Doc."""
        try:
            logger.info(
                "Getting Google Doc content",
                data={"user_id": user_id, "document_id": document_id},
            )

            endpoint = f"{self.docs_base_url}/documents/{document_id}"
            result = self._make_request("GET", endpoint, user_id)

            if result["success"]:
                # Extract text content from the document
                document_data = result["data"]
                content = self._extract_document_text(document_data)
                result["data"]["extracted_text"] = content
                logger.info(
                    "Successfully retrieved Google Doc content",
                    data={"user_id": user_id, "document_id": document_id},
                )

            return result

        except Exception as e:
            logger.error(f"Error getting Google Doc content: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to get Google Doc content: {str(e)}",
                "code": "DOCS_ERROR",
            }

    def _extract_document_text(self, document_data: Dict) -> str:
        """Extract plain text from Google Docs document structure."""
        try:
            content = document_data.get("body", {}).get("content", [])
            text_parts = []

            for element in content:
                if "paragraph" in element:
                    paragraph = element["paragraph"]
                    paragraph_text = ""

                    for text_element in paragraph.get("elements", []):
                        if "textRun" in text_element:
                            paragraph_text += text_element["textRun"].get("content", "")

                    if paragraph_text.strip():
                        text_parts.append(paragraph_text.strip())

                elif "table" in element:
                    # Handle tables
                    table = element["table"]
                    for row in table.get("tableRows", []):
                        row_text = []
                        for cell in row.get("tableCells", []):
                            cell_text = ""
                            for cell_element in cell.get("content", []):
                                if "paragraph" in cell_element:
                                    for text_element in cell_element["paragraph"].get(
                                        "elements", []
                                    ):
                                        if "textRun" in text_element:
                                            cell_text += text_element["textRun"].get(
                                                "content", ""
                                            )
                            row_text.append(cell_text.strip())
                        if any(row_text):
                            text_parts.append(" | ".join(row_text))

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extracting document text: {str(e)}")
            return "Could not extract text content from document"


# Initialize the integration
google_docs = GoogleDocsIntegration()


@tool
def list_documents(user_id: str, max_results: int = 10) -> str:
    """Fetch recent Google Docs from the user's Drive."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."

        result = google_docs.list_documents(user_id, max_results)

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Google Drive is not connected. Please connect your Google account to use document features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            else:
                return f"Error: {result['error']}"

        files = result["data"].get("files", [])
        if not files:
            return "No Google Docs found in your Drive."

        # Format documents for display
        formatted_docs = []
        for doc in files:
            name = doc.get("name", "Untitled")
            doc_id = doc.get("id", "")
            modified_time = doc.get("modifiedTime", "")
            web_link = doc.get("webViewLink", "")

            if modified_time:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    formatted_time = modified_time
            else:
                formatted_time = "Unknown"

            doc_info = f"• {name} (ID: {doc_id})\n  Last modified: {formatted_time}"
            if web_link:
                doc_info += f"\n  Link: {web_link}"

            formatted_docs.append(doc_info)

        return "Your recent Google Docs:\n\n" + "\n\n".join(formatted_docs)

    except Exception as e:
        logger.error("Error in list_documents tool", error=str(e))
        return f"Error fetching documents: {str(e)}"


@tool
def get_document_content(user_id: str, document_id: str) -> str:
    """Retrieve the content of a specific Google Doc."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        if not document_id or not document_id.strip():
            return "Error: document_id is required and cannot be empty."

        result = google_docs.get_document_content(user_id, document_id)

        if not result["success"]:
            if result["code"] == "NO_GOOGLE_ACCOUNT":
                return "Your Google Drive is not connected. Please connect your Google account to use document features."
            elif result["code"] == "INVALID_TOKEN":
                return "Your Google account needs to be reconnected. Please go to Settings and reconnect your Google account."
            elif result["code"] == "DOC_NOT_FOUND":
                return "The requested document was not found."
            else:
                return f"Error: {result['error']}"

        document_data = result["data"]
        title = document_data.get("title", "Untitled Document")
        extracted_text = document_data.get("extracted_text", "No content available")

        formatted_content = f"""
Document: {title}
Document ID: {document_id}

Content:
{extracted_text}
        """.strip()

        return formatted_content

    except Exception as e:
        logger.error("Error in get_document_content tool", error=str(e))
        return f"Error retrieving document content: {str(e)}"
