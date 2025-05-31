"""
Test suite for WhatsApp memory management tools using pytest.
"""

import pytest


class TestMemoryTools:
    """Test class for memory management tools functionality."""

    def test_memory_tools_initialization(self, whatsapp_tools):
        """Test that memory tools are properly initialized."""
        all_tools = whatsapp_tools.get_all_tools()
        tool_names = [tool.name for tool in all_tools]

        expected_memory_tools = [
            "search_memories",
            "add_memory",
            "get_all_memories",
            "delete_memory",
            "update_memory",
        ]

        for tool_name in expected_memory_tools:
            assert tool_name in tool_names, f"Memory tool '{tool_name}' not found"

    def test_add_memory_tool(self, tool_map):
        """Test the add_memory tool."""
        assert "add_memory" in tool_map

        test_content = "This is a test memory for pytest"
        test_user_id = "pytest_user_123"

        result = tool_map["add_memory"].invoke(
            {"content": test_content, "user_id": test_user_id}
        )

        assert isinstance(result, str)
        assert "Successfully stored" in result or "stored" in result.lower()
        assert test_content in result

    def test_add_memory_tool_with_metadata(self, tool_map):
        """Test the add_memory tool with metadata."""
        assert "add_memory" in tool_map

        test_content = "Test memory with metadata"
        test_user_id = "pytest_user_123"
        test_metadata = {"source": "pytest", "category": "test"}

        result = tool_map["add_memory"].invoke(
            {
                "content": test_content,
                "user_id": test_user_id,
                "metadata": test_metadata,
            }
        )

        assert isinstance(result, str)
        assert "Successfully stored" in result or "stored" in result.lower()

    def test_search_memories_tool(self, tool_map):
        """Test the search_memories tool."""
        assert "search_memories" in tool_map

        # First add a memory to search for
        test_content = "Unique pytest search test memory"
        test_user_id = "pytest_search_user"

        add_result = tool_map["add_memory"].invoke(
            {"content": test_content, "user_id": test_user_id}
        )
        assert "Successfully stored" in add_result or "stored" in add_result.lower()

        # Now search for it
        search_result = tool_map["search_memories"].invoke(
            {"query": "pytest search test", "user_id": test_user_id, "limit": 5}
        )

        assert isinstance(search_result, str)
        # Should either find memories or indicate none found
        assert (
            "Found" in search_result and "memories" in search_result
        ) or "No relevant memories found" in search_result

    def test_search_memories_tool_no_results(self, tool_map):
        """Test the search_memories tool when no memories are found."""
        assert "search_memories" in tool_map

        result = tool_map["search_memories"].invoke(
            {
                "query": "nonexistent_unique_query_12345",
                "user_id": "nonexistent_user_12345",
                "limit": 5,
            }
        )

        assert isinstance(result, str)
        assert "No relevant memories found" in result

    def test_get_all_memories_tool(self, tool_map):
        """Test the get_all_memories tool."""
        assert "get_all_memories" in tool_map

        test_user_id = "pytest_getall_user"

        # Add a test memory first
        add_result = tool_map["add_memory"].invoke(
            {"content": "Test memory for get_all test", "user_id": test_user_id}
        )
        assert "Successfully stored" in add_result or "stored" in add_result.lower()

        # Get all memories
        result = tool_map["get_all_memories"].invoke(
            {"user_id": test_user_id, "limit": 10}
        )

        assert isinstance(result, str)
        # Should either find memories or indicate none found
        assert (
            "Found" in result and "memories" in result
        ) or "No memories found" in result

    def test_get_all_memories_tool_no_memories(self, tool_map):
        """Test the get_all_memories tool when user has no memories."""
        assert "get_all_memories" in tool_map

        result = tool_map["get_all_memories"].invoke(
            {"user_id": "nonexistent_user_no_memories", "limit": 10}
        )

        assert isinstance(result, str)
        assert "No memories found" in result

    def test_delete_memory_tool_invalid_id(self, tool_map):
        """Test the delete_memory tool with invalid memory ID."""
        assert "delete_memory" in tool_map

        result = tool_map["delete_memory"].invoke(
            {"memory_id": "nonexistent_memory_id_12345", "user_id": "test_user"}
        )

        assert isinstance(result, str)
        # Should indicate failure or error
        assert "Failed" in result or "Error" in result or "not found" in result.lower()

    def test_update_memory_tool_invalid_id(self, tool_map):
        """Test the update_memory tool with invalid memory ID."""
        assert "update_memory" in tool_map

        result = tool_map["update_memory"].invoke(
            {
                "memory_id": "nonexistent_memory_id_12345",
                "new_content": "Updated content",
                "user_id": "test_user",
            }
        )

        assert isinstance(result, str)
        # Should indicate failure or error
        assert "Failed" in result or "Error" in result or "not found" in result.lower()

    def test_memory_tools_error_handling(self, tool_map):
        """Test that memory tools handle errors gracefully."""
        memory_tools = [
            "search_memories",
            "add_memory",
            "get_all_memories",
            "delete_memory",
            "update_memory",
        ]

        for tool_name in memory_tools:
            assert tool_name in tool_map
            tool = tool_map[tool_name]

            # Test with empty/invalid parameters
            try:
                if tool_name == "search_memories":
                    result = tool.invoke({"query": "", "user_id": ""})
                elif tool_name == "add_memory":
                    result = tool.invoke({"content": "", "user_id": ""})
                elif tool_name == "get_all_memories":
                    result = tool.invoke({"user_id": ""})
                elif tool_name == "delete_memory":
                    result = tool.invoke({"memory_id": "", "user_id": ""})
                elif tool_name == "update_memory":
                    result = tool.invoke(
                        {"memory_id": "", "new_content": "", "user_id": ""}
                    )

                # Should return a string response, not crash
                assert isinstance(result, str)

            except Exception as e:
                # If an exception is raised, it should be handled gracefully
                pytest.fail(
                    f"Tool {tool_name} should handle invalid parameters gracefully, but raised: {e}"
                )

    def test_memory_tools_have_descriptions(self, whatsapp_tools):
        """Test that all memory tools have proper descriptions."""
        all_tools = whatsapp_tools.get_all_tools()
        memory_tool_names = [
            "search_memories",
            "add_memory",
            "get_all_memories",
            "delete_memory",
            "update_memory",
        ]

        for tool in all_tools:
            if tool.name in memory_tool_names:
                assert hasattr(tool, "description"), (
                    f"Memory tool {tool.name} missing description"
                )
                assert tool.description, (
                    f"Memory tool {tool.name} has empty description"
                )
                assert len(tool.description) > 20, (
                    f"Memory tool {tool.name} description too short"
                )

                # Check that description mentions what the tool does
                description_lower = tool.description.lower()
                if tool.name == "search_memories":
                    assert "search" in description_lower
                elif tool.name == "add_memory":
                    assert "store" in description_lower or "add" in description_lower
                elif tool.name == "get_all_memories":
                    assert "retrieve" in description_lower or "get" in description_lower
                elif tool.name == "delete_memory":
                    assert "delete" in description_lower
                elif tool.name == "update_memory":
                    assert "update" in description_lower
