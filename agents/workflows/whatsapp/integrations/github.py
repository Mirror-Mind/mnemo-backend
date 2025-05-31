"""
GitHub integration tools for WhatsApp workflow.
"""

from typing import Any, Dict, Optional

import requests
from langchain_core.tools import tool

from helpers.logger_config import logger
from models.user_models import SessionLocal
from repository.user_repository import UserRepository


class GitHubIntegration:
    """GitHub API integration."""

    def __init__(self):
        """Initialize GitHub integration."""
        self.base_url = "https://api.github.com"

    def _get_access_token(self, user_id: str) -> Optional[str]:
        """Get GitHub access token for user."""
        try:
            db = SessionLocal()
            repo = UserRepository(db)
            token = repo.get_github_access_token(user_id)
            db.close()
            return token
        except Exception as e:
            logger.error(
                f"Error getting GitHub access token: {str(e)}", user_id=user_id
            )
            return None

    def _make_request(
        self, method: str, endpoint: str, user_id: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to GitHub API."""
        access_token = self._get_access_token(user_id)
        if not access_token:
            return {
                "success": False,
                "error": "No GitHub account connected",
                "code": "NO_GITHUB_ACCOUNT",
            }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
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
                    "error": "GitHub authentication failed. Please reconnect your GitHub account.",
                    "code": "INVALID_TOKEN",
                }

            if response.status_code == 404:
                return {
                    "success": False,
                    "error": "Resource not found",
                    "code": "NOT_FOUND",
                }

            if not response.ok:
                return {
                    "success": False,
                    "error": f"GitHub API error: {response.status_code}",
                    "code": "GITHUB_API_ERROR",
                }

            return {
                "success": True,
                "data": response.json() if response.content else {},
            }

        except Exception as e:
            logger.error(f"Error making GitHub API request: {str(e)}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "code": "REQUEST_ERROR",
            }

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get GitHub user information."""
        try:
            logger.info("Getting GitHub user info", user_id=user_id)

            result = self._make_request("GET", "/user", user_id)

            if result["success"]:
                logger.info("Successfully retrieved GitHub user info", user_id=user_id)

            return result

        except Exception as e:
            logger.error(
                "Error getting GitHub user info", error=str(e), user_id=user_id
            )
            return {
                "success": False,
                "error": f"Failed to get GitHub user info: {str(e)}",
                "code": "GITHUB_ERROR",
            }

    def list_pull_requests(self, user_id: str) -> Dict[str, Any]:
        """List open pull requests created by the user."""
        try:
            logger.info("Listing GitHub pull requests", user_id=user_id)

            # First get user info to get username
            user_info_result = self.get_user_info(user_id)
            if not user_info_result["success"]:
                return user_info_result

            username = user_info_result["data"].get("login")
            if not username:
                return {
                    "success": False,
                    "error": "Could not determine GitHub username",
                    "code": "NO_USERNAME",
                }

            # Search for pull requests created by the user
            search_query = f"is:pr+author:{username}+is:open"
            endpoint = f"/search/issues?q={search_query}"

            result = self._make_request("GET", endpoint, user_id)

            if result["success"]:
                items = result["data"].get("items", [])

                # Transform the data to include repository information
                pull_requests = []
                for item in items:
                    # Extract repo owner and name from the HTML URL
                    html_url = item.get("html_url", "")
                    url_parts = html_url.split("/") if html_url else []

                    if len(url_parts) >= 5:
                        repo_owner = url_parts[3]
                        repo_name = url_parts[4]

                        pull_requests.append(
                            {
                                "id": str(item.get("id", "")),
                                "title": item.get("title", ""),
                                "number": item.get("number", 0),
                                "state": item.get("state", ""),
                                "html_url": html_url,
                                "created_at": item.get("created_at", ""),
                                "repository": {
                                    "name": repo_name,
                                    "full_name": f"{repo_owner}/{repo_name}",
                                },
                            }
                        )

                result["data"] = pull_requests
                logger.info(
                    "Successfully listed GitHub pull requests",
                    data={"user_id": user_id, "count": len(pull_requests)},
                )

            return result

        except Exception as e:
            logger.error(
                f"Error listing GitHub pull requests: {str(e)}", user_id=user_id
            )
            return {
                "success": False,
                "error": f"Failed to list GitHub pull requests: {str(e)}",
                "code": "GITHUB_ERROR",
            }

    def get_pull_request_details(
        self, user_id: str, owner: str, repo: str, pull_request_number: int
    ) -> Dict[str, Any]:
        """Get details of a specific pull request."""
        try:
            logger.info(
                "Getting GitHub PR details",
                data={
                    "user_id": user_id,
                    "owner": owner,
                    "repo": repo,
                    "pr_number": pull_request_number,
                },
            )

            endpoint = f"/repos/{owner}/{repo}/pulls/{pull_request_number}"
            result = self._make_request("GET", endpoint, user_id)

            if result["success"]:
                pr_data = result["data"]

                # Format the response with useful information
                formatted_data = {
                    "id": str(pr_data.get("id", "")),
                    "title": pr_data.get("title", ""),
                    "number": pr_data.get("number", 0),
                    "state": pr_data.get("state", ""),
                    "html_url": pr_data.get("html_url", ""),
                    "created_at": pr_data.get("created_at", ""),
                    "updated_at": pr_data.get("updated_at", ""),
                    "body": pr_data.get("body", ""),
                    "user": {
                        "login": pr_data.get("user", {}).get("login", ""),
                        "avatar_url": pr_data.get("user", {}).get("avatar_url", ""),
                    },
                    "repository": {"name": repo, "full_name": f"{owner}/{repo}"},
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "changed_files": pr_data.get("changed_files", 0),
                }

                result["data"] = formatted_data
                logger.info(
                    "Successfully retrieved GitHub PR details",
                    data={"user_id": user_id, "pr_number": pull_request_number},
                )

            return result

        except Exception as e:
            logger.error(f"Error getting GitHub PR details: {str(e)}", user_id=user_id)
            return {
                "success": False,
                "error": f"Failed to get GitHub PR details: {str(e)}",
                "code": "GITHUB_ERROR",
            }


# Initialize the integration
github = GitHubIntegration()


@tool
def list_github_pull_requests(user_id: str) -> str:
    """List open pull requests created by the user on GitHub."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."

        result = github.list_pull_requests(user_id)

        if not result["success"]:
            if result["code"] == "NO_GITHUB_ACCOUNT":
                return "You don't have a GitHub account connected. Please connect your GitHub account in the Providers section of your dashboard."
            elif result["code"] == "INVALID_TOKEN":
                return "Your GitHub account needs to be reconnected. Please go to Settings and reconnect your GitHub account."
            else:
                return f"Error: {result['error']}"

        pull_requests = result["data"]
        if not pull_requests:
            return "You don't have any open pull requests."

        # Format the response
        formatted_prs = []
        for pr in pull_requests:
            pr_info = f'• #{pr["number"]}: "{pr["title"]}" in {pr["repository"]["full_name"]}\n  URL: {pr["html_url"]}'
            formatted_prs.append(pr_info)

        return "Your open pull requests:\n\n" + "\n\n".join(formatted_prs)

    except Exception as e:
        logger.error("Error in list_github_pull_requests tool", error=str(e))
        return f"Error listing pull requests: {str(e)}"


@tool
def get_github_pull_request_details(
    user_id: str, owner: str, repo: str, pull_request_number: int
) -> str:
    """Get detailed information about a specific GitHub pull request."""
    try:
        if not user_id or not user_id.strip():
            return "Error: user_id is required and cannot be empty."
        if not owner or not owner.strip():
            return "Error: owner is required and cannot be empty."
        if not repo or not repo.strip():
            return "Error: repo is required and cannot be empty."
        if not pull_request_number:
            return "Error: pull_request_number is required."

        result = github.get_pull_request_details(
            user_id, owner, repo, pull_request_number
        )

        if not result["success"]:
            if result["code"] == "NO_GITHUB_ACCOUNT":
                return "You don't have a GitHub account connected. Please connect your GitHub account in the Providers section of your dashboard."
            elif result["code"] == "INVALID_TOKEN":
                return "Your GitHub account needs to be reconnected. Please go to Settings and reconnect your GitHub account."
            elif result["code"] == "NOT_FOUND":
                return "The requested pull request was not found."
            else:
                return f"Error: {result['error']}"

        pr = result["data"]

        # Format the response
        formatted_response = f"""
Pull Request #{pr["number"]}: "{pr["title"]}"
Repository: {pr["repository"]["full_name"]}
URL: {pr["html_url"]}
Status: {pr["state"]}
Created: {pr["created_at"]}
Last Updated: {pr["updated_at"]}
Author: {pr["user"]["login"]}

Description:
{pr["body"] or "(No description provided)"}

Changes:
- Added {pr["additions"]} lines
- Removed {pr["deletions"]} lines
- Changed {pr["changed_files"]} files
        """.strip()

        return formatted_response

    except Exception as e:
        logger.error("Error in get_github_pull_request_details tool", error=str(e))
        return f"Error getting pull request details: {str(e)}"
