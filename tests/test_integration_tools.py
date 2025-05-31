"""
Tests for WhatsApp workflow integration tools.
"""

from unittest.mock import Mock, patch

import pytest

from agents.workflows.whatsapp.integrations.github import (
    GitHubIntegration,
    get_github_pull_request_details,
    list_github_pull_requests,
)
from agents.workflows.whatsapp.integrations.gmail import (
    GmailIntegration,
    send_gmail_message,
)
from agents.workflows.whatsapp.integrations.google_calendar import (
    GoogleCalendarIntegration,
    create_calendar_event,
    list_calendar_events,
)
from agents.workflows.whatsapp.integrations.google_docs import (
    GoogleDocsIntegration,
    get_document_content,
)


class TestGoogleCalendarIntegration:
    """Test Google Calendar integration."""

    @pytest.fixture
    def calendar_integration(self):
        """Create a calendar integration instance."""
        return GoogleCalendarIntegration()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch(
            "agents.workflows.whatsapp.integrations.google_calendar.SessionLocal"
        ) as mock_session:
            mock_db = Mock()
            mock_session.return_value = mock_db
            yield mock_db

    @pytest.fixture
    def mock_user_repo(self):
        """Mock user repository."""
        with patch(
            "agents.workflows.whatsapp.integrations.google_calendar.UserRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    def test_get_access_token_success(
        self, calendar_integration, mock_db_session, mock_user_repo
    ):
        """Test successful access token retrieval."""
        mock_user_repo.get_google_access_token.return_value = "test_token"

        token = calendar_integration._get_access_token("test_user_id")

        assert token == "test_token"
        mock_user_repo.get_google_access_token.assert_called_once_with("test_user_id")
        mock_db_session.close.assert_called_once()

    def test_get_access_token_no_token(
        self, calendar_integration, mock_db_session, mock_user_repo
    ):
        """Test access token retrieval when no token exists."""
        mock_user_repo.get_google_access_token.return_value = None

        token = calendar_integration._get_access_token("test_user_id")

        assert token is None

    @patch("agents.workflows.whatsapp.integrations.google_calendar.requests.get")
    def test_list_events_success(self, mock_get, calendar_integration, mock_user_repo):
        """Test successful event listing."""
        mock_user_repo.get_google_access_token.return_value = "test_token"

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "summary": "Test Event",
                    "start": {"dateTime": "2024-01-01T10:00:00Z"},
                    "end": {"dateTime": "2024-01-01T11:00:00Z"},
                }
            ]
        }
        mock_get.return_value = mock_response

        result = calendar_integration.list_events("test_user_id", 10)

        assert result["success"] is True
        assert len(result["data"]["items"]) == 1
        assert result["data"]["items"][0]["summary"] == "Test Event"

    @patch("agents.workflows.whatsapp.integrations.google_calendar.requests.post")
    def test_create_event_success(
        self, mock_post, calendar_integration, mock_user_repo
    ):
        """Test successful event creation."""
        mock_user_repo.get_google_access_token.return_value = "test_token"

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "event_123",
            "summary": "Test Event",
            "htmlLink": "https://calendar.google.com/event?eid=event_123",
        }
        mock_post.return_value = mock_response

        result = calendar_integration.create_event(
            "test_user_id",
            "Test Event",
            "2024-01-01T10:00:00+00:00",
            "2024-01-01T11:00:00+00:00",
            "Test description",
        )

        assert result["success"] is True
        assert result["data"]["id"] == "event_123"

    def test_list_calendar_events_tool_no_user_id(self):
        """Test list calendar events tool with no user ID."""
        result = list_calendar_events.invoke({"user_id": ""})
        assert "Error: user_id is required" in result

    def test_create_calendar_event_tool_missing_params(self):
        """Test create calendar event tool with missing parameters."""
        result = create_calendar_event.invoke(
            {"user_id": "user_id", "summary": "", "start": "start", "end": "end"}
        )
        assert "Error: summary is required" in result


class TestGmailIntegration:
    """Test Gmail integration."""

    @pytest.fixture
    def gmail_integration(self):
        """Create a Gmail integration instance."""
        return GmailIntegration()

    @pytest.fixture
    def mock_user_repo(self):
        """Mock user repository."""
        with patch(
            "agents.workflows.whatsapp.integrations.gmail.UserRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    @patch("agents.workflows.whatsapp.integrations.gmail.requests.get")
    def test_list_messages_success(self, mock_get, gmail_integration, mock_user_repo):
        """Test successful message listing."""
        mock_user_repo.get_google_access_token.return_value = "test_token"

        # Mock the messages list response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "msg_123"}]}
        mock_get.return_value = mock_response

        # Mock the get_message method to avoid recursive calls
        with patch.object(gmail_integration, "get_message") as mock_get_message:
            mock_get_message.return_value = {
                "success": True,
                "data": {
                    "id": "msg_123",
                    "subject": "Test Subject",
                    "from": "test@example.com",
                    "snippet": "Test snippet",
                },
            }

            result = gmail_integration.list_messages("test_user_id", 10)

            assert result["success"] is True
            assert len(result["data"]["messages"]) == 1

    @patch("agents.workflows.whatsapp.integrations.gmail.requests.post")
    def test_send_message_success(self, mock_post, gmail_integration, mock_user_repo):
        """Test successful message sending."""
        mock_user_repo.get_google_access_token.return_value = "test_token"

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_sent_123",
            "threadId": "thread_123",
        }
        mock_post.return_value = mock_response

        result = gmail_integration.send_message(
            "test_user_id", "recipient@example.com", "Test Subject", "Test body"
        )

        assert result["success"] is True
        assert result["data"]["id"] == "msg_sent_123"

    def test_send_gmail_message_tool_missing_params(self):
        """Test send Gmail message tool with missing parameters."""
        result = send_gmail_message.invoke(
            {"user_id": "user_id", "to": "", "subject": "subject", "body": "body"}
        )
        assert "Error: to email is required" in result


class TestGoogleDocsIntegration:
    """Test Google Docs integration."""

    @pytest.fixture
    def docs_integration(self):
        """Create a Google Docs integration instance."""
        return GoogleDocsIntegration()

    @pytest.fixture
    def mock_user_repo(self):
        """Mock user repository."""
        with patch(
            "agents.workflows.whatsapp.integrations.google_docs.UserRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    @patch("agents.workflows.whatsapp.integrations.google_docs.requests.get")
    def test_list_documents_success(self, mock_get, docs_integration, mock_user_repo):
        """Test successful document listing."""
        mock_user_repo.get_google_access_token.return_value = "test_token"

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "files": [
                {
                    "id": "doc_123",
                    "name": "Test Document",
                    "modifiedTime": "2024-01-01T10:00:00Z",
                    "webViewLink": "https://docs.google.com/document/d/doc_123",
                }
            ]
        }
        mock_get.return_value = mock_response

        result = docs_integration.list_documents("test_user_id", 10)

        assert result["success"] is True
        assert len(result["data"]["files"]) == 1
        assert result["data"]["files"][0]["name"] == "Test Document"

    @patch("agents.workflows.whatsapp.integrations.google_docs.requests.get")
    def test_get_document_content_success(
        self, mock_get, docs_integration, mock_user_repo
    ):
        """Test successful document content retrieval."""
        mock_user_repo.get_google_access_token.return_value = "test_token"

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Document",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Test content"}}]
                        }
                    }
                ]
            },
        }
        mock_get.return_value = mock_response

        result = docs_integration.get_document_content("test_user_id", "doc_123")

        assert result["success"] is True
        assert "Test content" in result["data"]["extracted_text"]

    def test_get_document_content_tool_missing_params(self):
        """Test get document content tool with missing parameters."""
        result = get_document_content.invoke({"user_id": "user_id", "document_id": ""})
        assert "Error: document_id is required" in result


class TestGitHubIntegration:
    """Test GitHub integration."""

    @pytest.fixture
    def github_integration(self):
        """Create a GitHub integration instance."""
        return GitHubIntegration()

    @pytest.fixture
    def mock_user_repo(self):
        """Mock user repository."""
        with patch(
            "agents.workflows.whatsapp.integrations.github.UserRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    @patch("agents.workflows.whatsapp.integrations.github.requests.get")
    def test_get_user_info_success(self, mock_get, github_integration, mock_user_repo):
        """Test successful user info retrieval."""
        mock_user_repo.get_github_access_token.return_value = "test_token"

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "id": 12345,
            "avatar_url": "https://github.com/testuser.png",
        }
        mock_get.return_value = mock_response

        result = github_integration.get_user_info("test_user_id")

        assert result["success"] is True
        assert result["data"]["login"] == "testuser"

    @patch("agents.workflows.whatsapp.integrations.github.requests.get")
    def test_list_pull_requests_success(
        self, mock_get, github_integration, mock_user_repo
    ):
        """Test successful pull request listing."""
        mock_user_repo.get_github_access_token.return_value = "test_token"

        # Mock user info response
        user_response = Mock()
        user_response.ok = True
        user_response.status_code = 200
        user_response.json.return_value = {"login": "testuser"}

        # Mock search response
        search_response = Mock()
        search_response.ok = True
        search_response.status_code = 200
        search_response.json.return_value = {
            "items": [
                {
                    "id": 123,
                    "title": "Test PR",
                    "number": 1,
                    "state": "open",
                    "html_url": "https://github.com/owner/repo/pull/1",
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ]
        }

        mock_get.side_effect = [user_response, search_response]

        result = github_integration.list_pull_requests("test_user_id")

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["title"] == "Test PR"

    @patch("agents.workflows.whatsapp.integrations.github.requests.get")
    def test_get_pull_request_details_success(
        self, mock_get, github_integration, mock_user_repo
    ):
        """Test successful pull request details retrieval."""
        mock_user_repo.get_github_access_token.return_value = "test_token"

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 123,
            "title": "Test PR",
            "number": 1,
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/1",
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T11:00:00Z",
            "body": "Test PR description",
            "user": {"login": "testuser"},
            "additions": 10,
            "deletions": 5,
            "changed_files": 2,
        }
        mock_get.return_value = mock_response

        result = github_integration.get_pull_request_details(
            "test_user_id", "owner", "repo", 1
        )

        assert result["success"] is True
        assert result["data"]["title"] == "Test PR"
        assert result["data"]["additions"] == 10

    def test_get_github_pull_request_details_tool_missing_params(self):
        """Test get GitHub PR details tool with missing parameters."""
        result = get_github_pull_request_details.invoke(
            {
                "user_id": "user_id",
                "owner": "",
                "repo": "repo",
                "pull_request_number": 1,
            }
        )
        assert "Error: owner is required" in result


class TestErrorHandling:
    """Test error handling across all integrations."""

    def test_no_access_token_google_calendar(self):
        """Test Google Calendar with no access token."""
        with patch(
            "agents.workflows.whatsapp.integrations.google_calendar.UserRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_google_access_token.return_value = None

            result = list_calendar_events.invoke({"user_id": "test_user_id"})
            assert "Google Calendar is not connected" in result

    def test_no_access_token_github(self):
        """Test GitHub with no access token."""
        with patch(
            "agents.workflows.whatsapp.integrations.github.UserRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_github_access_token.return_value = None

            result = list_github_pull_requests.invoke({"user_id": "test_user_id"})
            assert "GitHub account connected" in result

    def test_invalid_token_response(self):
        """Test handling of invalid token responses."""
        with patch(
            "agents.workflows.whatsapp.integrations.google_calendar.UserRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_google_access_token.return_value = "invalid_token"

            with patch(
                "agents.workflows.whatsapp.integrations.google_calendar.requests.get"
            ) as mock_get:
                mock_response = Mock()
                mock_response.ok = False
                mock_response.status_code = 401
                mock_get.return_value = mock_response

                result = list_calendar_events.invoke({"user_id": "test_user_id"})
                assert "reconnect your Google account" in result


if __name__ == "__main__":
    pytest.main([__file__])
