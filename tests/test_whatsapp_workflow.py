"""
Test suite for WhatsApp workflow nodes and integration using pytest.
"""

import pytest
from langchain_core.messages import HumanMessage


class TestWhatsAppWorkflow:
    """Test class for WhatsApp workflow functionality."""

    def test_whatsapp_nodes_initialization(self, whatsapp_nodes):
        """Test that WhatsApp nodes are properly initialized."""
        assert whatsapp_nodes is not None
        assert whatsapp_nodes.workflow_name == "test_workflow"
        assert whatsapp_nodes.tools is not None
        assert whatsapp_nodes.memory_manager is not None
        assert whatsapp_nodes.llm_wrapper is not None
        assert whatsapp_nodes.model_name is not None

    def test_process_message_node_valid_message(
        self, whatsapp_nodes, sample_message_state
    ):
        """Test processing a valid message."""
        result = whatsapp_nodes.process_message_node(sample_message_state)

        assert isinstance(result, dict)
        assert "error" not in result or not result["error"]
        assert result.get("is_processing") is True
        assert "memory_context" in result
        assert result.get("user_id") == sample_message_state["user_id"]

    def test_process_message_node_no_messages(self, whatsapp_nodes, sample_user_state):
        """Test processing when no messages are provided."""
        state_no_messages = {**sample_user_state, "messages": []}

        result = whatsapp_nodes.process_message_node(state_no_messages)

        assert isinstance(result, dict)
        assert "error" in result
        assert "No messages to process" in result["error"]
        assert result.get("finished") is True

    def test_process_message_node_empty_state(self, whatsapp_nodes):
        """Test processing with empty state."""
        empty_state = {}

        result = whatsapp_nodes.process_message_node(empty_state)

        assert isinstance(result, dict)
        assert "error" in result
        assert result.get("finished") is True

    def test_generate_response_node_valid_state(
        self, whatsapp_nodes, sample_message_state
    ):
        """Test generating response with valid state."""
        # First process the message
        processed_state = whatsapp_nodes.process_message_node(sample_message_state)

        # Then generate response
        result = whatsapp_nodes.generate_response_node(processed_state)

        assert isinstance(result, dict)
        assert result.get("is_processing") is False
        assert result.get("finished") is True

        # Check if response was generated successfully
        if "error" not in result:
            assert "response_content" in result
            assert "response_type" in result
            assert len(result.get("messages", [])) > len(
                sample_message_state["messages"]
            )

    def test_generate_response_node_no_messages(
        self, whatsapp_nodes, sample_user_state
    ):
        """Test generating response when no messages are provided."""
        state_no_messages = {**sample_user_state, "messages": []}

        result = whatsapp_nodes.generate_response_node(state_no_messages)

        assert isinstance(result, dict)
        assert "error" in result
        assert "No messages to generate response for" in result["error"]
        assert result.get("finished") is True

    def test_format_whatsapp_response_text(self, whatsapp_nodes):
        """Test formatting text response for WhatsApp."""
        response_content = {
            "message_type": "text",
            "text": "Hello, this is a test response!",
        }

        result = whatsapp_nodes.format_whatsapp_response(response_content)

        assert isinstance(result, dict)
        assert result["messaging_product"] == "whatsapp"
        assert result["type"] == "text"
        assert result["text"]["body"] == "Hello, this is a test response!"
        assert result["to"] == ""  # Should be empty, filled by webhook handler

    def test_format_whatsapp_response_interactive_button(self, whatsapp_nodes):
        """Test formatting interactive button response for WhatsApp."""
        response_content = {
            "message_type": "interactive",
            "type": "button",
            "body": {"text": "Choose an option:"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "option_1", "title": "Option 1"}}
                ]
            },
        }

        result = whatsapp_nodes.format_whatsapp_response(response_content)

        assert isinstance(result, dict)
        assert result["messaging_product"] == "whatsapp"
        assert result["type"] == "interactive"
        assert result["interactive"]["type"] == "button"
        assert "body" in result["interactive"]
        assert "action" in result["interactive"]

    def test_format_whatsapp_response_long_button_title(self, whatsapp_nodes):
        """Test formatting response with button title that's too long."""
        response_content = {
            "message_type": "interactive",
            "type": "button",
            "body": {"text": "Choose an option:"},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "option_1",
                            "title": "This is a very long button title that exceeds 20 characters",
                        },
                    }
                ]
            },
        }

        result = whatsapp_nodes.format_whatsapp_response(response_content)

        assert isinstance(result, dict)
        button_title = result["interactive"]["action"]["buttons"][0]["reply"]["title"]
        assert len(button_title) <= 20, (
            "Button title should be truncated to 20 characters"
        )

    def test_format_whatsapp_response_fallback(self, whatsapp_nodes):
        """Test formatting response with unknown message type (should fallback to text)."""
        response_content = {"message_type": "unknown_type", "some_data": "test"}

        result = whatsapp_nodes.format_whatsapp_response(response_content)

        assert isinstance(result, dict)
        assert result["messaging_product"] == "whatsapp"
        assert result["type"] == "text"
        assert "I didn't understand that" in result["text"]["body"]

    def test_format_whatsapp_response_error_handling(self, whatsapp_nodes):
        """Test formatting response when an error occurs."""
        # Pass invalid data that should cause an error
        invalid_response_content = None

        result = whatsapp_nodes.format_whatsapp_response(invalid_response_content)

        assert isinstance(result, dict)
        assert result["messaging_product"] == "whatsapp"
        assert result["type"] == "text"
        assert "Sorry, I encountered an error" in result["text"]["body"]

    @pytest.mark.parametrize(
        "message_content",
        [
            "What time is it?",
            "Calculate 25 * 4",
            "Generate a random number",
            "Count words in this text",
            "Reverse this text: hello",
        ],
    )
    def test_workflow_with_tool_triggering_messages(
        self, whatsapp_nodes, sample_user_state, message_content
    ):
        """Test workflow with messages that should trigger tools."""
        test_state = {
            **sample_user_state,
            "messages": [HumanMessage(content=message_content)],
        }

        # Process message
        processed_state = whatsapp_nodes.process_message_node(test_state)
        assert processed_state.get("is_processing") is True

        # Generate response
        response_state = whatsapp_nodes.generate_response_node(processed_state)

        # Should complete without errors
        assert response_state.get("finished") is True
        assert response_state.get("is_processing") is False

        # Should have generated some response
        if "error" not in response_state:
            assert "response_content" in response_state
            assert len(response_state.get("messages", [])) > 1

    def test_workflow_memory_integration(self, whatsapp_nodes, sample_user_state):
        """Test that workflow properly integrates with memory system."""
        # Send a message that should be stored in memory
        test_state = {
            **sample_user_state,
            "messages": [
                HumanMessage(content="Remember that my favorite color is blue")
            ],
        }

        # Process and generate response
        processed_state = whatsapp_nodes.process_message_node(test_state)
        response_state = whatsapp_nodes.generate_response_node(processed_state)

        # Should complete successfully
        assert response_state.get("finished") is True

        # Now send another message that might reference the memory
        follow_up_state = {
            **sample_user_state,
            "messages": [HumanMessage(content="What's my favorite color?")],
        }

        # Process the follow-up message
        processed_followup = whatsapp_nodes.process_message_node(follow_up_state)

        # Should have memory context
        assert "memory_context" in processed_followup
        # Memory context might be empty if the memory system isn't fully set up,
        # but the key should exist

    def test_workflow_error_recovery(self, whatsapp_nodes):
        """Test that workflow handles errors gracefully."""
        # Test with malformed state
        malformed_state = {
            "messages": "not_a_list",  # Should be a list
            "user_id": None,
            "session_id": "",
        }

        # Should not crash, should return error state
        result = whatsapp_nodes.process_message_node(malformed_state)
        assert isinstance(result, dict)
        assert "error" in result or result.get("finished") is True

    def test_workflow_state_preservation(self, whatsapp_nodes, sample_message_state):
        """Test that workflow preserves important state information."""
        original_user_id = sample_message_state["user_id"]
        original_session_id = sample_message_state["session_id"]

        # Process message
        processed_state = whatsapp_nodes.process_message_node(sample_message_state)

        # Important state should be preserved
        assert processed_state.get("user_id") == original_user_id
        assert processed_state.get("session_id") == original_session_id
        assert "messages" in processed_state

        # Generate response
        response_state = whatsapp_nodes.generate_response_node(processed_state)

        # State should still be preserved
        assert response_state.get("user_id") == original_user_id
        assert response_state.get("session_id") == original_session_id
