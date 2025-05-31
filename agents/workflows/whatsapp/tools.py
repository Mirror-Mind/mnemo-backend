"""
Tools for WhatsApp workflow including memory management and external integrations.
"""

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from helpers.logger_config import logger

from .memory import WhatsAppMemoryManager


class WhatsAppTools:
    """Collection of tools for WhatsApp workflow."""

    def __init__(self, memory_manager: WhatsAppMemoryManager):
        """Initialize tools with memory manager."""
        self.memory_manager = memory_manager
        self.memory_tools = self._create_memory_tools()
        self.integration_tools = self._create_integration_tools()

    def _create_memory_tools(self):
        """Create memory management tools as standalone functions."""
        memory_manager = self.memory_manager

        @tool
        def search_memories(query: str, user_id: str, limit: int = 5) -> str:
            """Search through stored memories to find relevant information from past conversations."""
            try:
                if not user_id or not user_id.strip():
                    return "Error: user_id is required and cannot be empty."

                results = memory_manager.search_memories(query, user_id, limit)
                if not results:
                    return "No relevant memories found for your query."

                memories = []
                for i, result in enumerate(results, 1):
                    memory_text = result.get("memory", str(result))
                    score = result.get("score", "N/A")
                    memories.append(f"{i}. {memory_text} (Score: {score})")

                return f"Found {len(results)} relevant memories:\n" + "\n".join(
                    memories
                )
            except Exception as e:
                logger.error("Error in search_memories tool", error=str(e))
                return f"Error searching memories: {str(e)}"

        @tool
        def add_memory(
            content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None
        ) -> str:
            """Store important information from the conversation for future reference."""
            try:
                if not user_id or not user_id.strip():
                    return "Error: user_id is required and cannot be empty."
                if not content or not content.strip():
                    return "Error: content is required and cannot be empty."

                success = memory_manager.add_single_memory(content, user_id, metadata)
                if success:
                    return f'Successfully stored the information: "{content}"'
                else:
                    return "Failed to store the information in memory."
            except Exception as e:
                logger.error("Error in add_memory tool", error=str(e))
                return f"Error storing memory: {str(e)}"

        @tool
        def get_all_memories(user_id: str, limit: int = 10) -> str:
            """Retrieve all stored memories for the current user."""
            try:
                if not user_id or not user_id.strip():
                    return "Error: user_id is required and cannot be empty."

                results = memory_manager.get_all_memories(user_id, limit)
                if not results:
                    return "No memories found for this user."

                memories = []
                for i, memory in enumerate(results, 1):
                    memory_text = memory.get("memory", str(memory))
                    memories.append(f"{i}. {memory_text}")

                return f"Found {len(results)} memories:\n" + "\n".join(memories)
            except Exception as e:
                logger.error("Error in get_all_memories tool", error=str(e))
                return f"Error retrieving memories: {str(e)}"

        @tool
        def delete_memory(memory_id: str, user_id: str) -> str:
            """Delete a specific memory by its ID."""
            try:
                if not memory_id or not memory_id.strip():
                    return "Error: memory_id is required and cannot be empty."
                if not user_id or not user_id.strip():
                    return "Error: user_id is required and cannot be empty."

                success = memory_manager.delete_memory(memory_id, user_id)
                if success:
                    return f"Successfully deleted memory with ID: {memory_id}"
                else:
                    return f"Failed to delete memory with ID: {memory_id}"
            except Exception as e:
                logger.error("Error in delete_memory tool", error=str(e))
                return f"Error deleting memory: {str(e)}"

        @tool
        def update_memory(memory_id: str, new_content: str, user_id: str) -> str:
            """Update an existing memory with new content."""
            try:
                if not memory_id or not memory_id.strip():
                    return "Error: memory_id is required and cannot be empty."
                if not new_content or not new_content.strip():
                    return "Error: new_content is required and cannot be empty."
                if not user_id or not user_id.strip():
                    return "Error: user_id is required and cannot be empty."

                success = memory_manager.update_memory(memory_id, new_content, user_id)
                if success:
                    return f"Successfully updated memory with ID: {memory_id}"
                else:
                    return f"Failed to update memory with ID: {memory_id}"
            except Exception as e:
                logger.error("Error in update_memory tool", error=str(e))
                return f"Error updating memory: {str(e)}"

        return [
            search_memories,
            add_memory,
            get_all_memories,
            delete_memory,
            update_memory,
        ]

    # External integration tools - now implemented with actual API calls
    def _create_integration_tools(self):
        """Create external integration tools."""
        # Import the integration tools
        from .integrations.github import (
            get_github_pull_request_details,
            list_github_pull_requests,
        )
        from .integrations.gmail import (
            list_gmail_messages,
            read_gmail_message,
            send_gmail_message,
        )
        from .integrations.google_calendar import (
            create_calendar_event,
            delete_calendar_event,
            list_calendar_events,
        )
        from .integrations.google_docs import get_document_content, list_documents
        
        # Import the new Perplexity search tools
        from .integrations.perplexity_search import (
            search_person_and_generate_intro,
            search_company_overview,
        )

        return [
            list_calendar_events,
            create_calendar_event,
            delete_calendar_event,
            list_gmail_messages,
            read_gmail_message,
            send_gmail_message,
            list_documents,
            get_document_content,
            list_github_pull_requests,
            get_github_pull_request_details,
            search_person_and_generate_intro,
            search_company_overview,
        ]

    def get_all_tools(self) -> List:
        """Get all available tools for the workflow."""
        tools = []

        # Add memory management tools
        tools.extend(self.memory_tools)

        # Add external integration tools
        tools.extend(self.integration_tools)

        return tools
