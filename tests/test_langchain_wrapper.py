"""
Test suite for LangChain wrapper functionality using pytest.
"""

import json
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.utils.langchain_wrapper import (
    LangChainWrapper,
    ResponseInterface,
    convert_to_langchain_messages,
    get_clean_messages,
)


class TestLangChainWrapper:
    """Test class for LangChain wrapper functionality."""

    def test_langchain_wrapper_initialization(self):
        """Test that LangChain wrapper initializes correctly."""
        wrapper = LangChainWrapper(workflow_name="test_workflow")

        assert wrapper.workflow_name == "test_workflow"
        assert wrapper._models == {}

    def test_get_clean_messages_valid_input(self):
        """Test get_clean_messages with valid input."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = get_clean_messages(messages)

        assert len(result) == 3
        assert all("role" in msg and "content" in msg for msg in result)
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"

    def test_get_clean_messages_invalid_input(self):
        """Test get_clean_messages with invalid input."""
        messages = [
            {"role": "user", "content": "Valid message"},
            {"invalid": "message"},  # Missing role and content
            "not_a_dict",  # Not a dictionary
            {"role": "user"},  # Missing content
            {"content": "Missing role"},  # Missing role
        ]

        result = get_clean_messages(messages)

        # Should only return the valid message
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Valid message"

    def test_convert_to_langchain_messages(self):
        """Test converting dictionary messages to LangChain message objects."""
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message"},
            {"role": "human", "content": "Human message"},
            {"role": "assistant", "content": "Assistant message"},
            {"role": "ai", "content": "AI message"},
            {"role": "unknown", "content": "Unknown role"},
        ]

        result = convert_to_langchain_messages(messages)

        assert len(result) == 6
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], HumanMessage)  # human -> HumanMessage
        assert isinstance(result[3], AIMessage)
        assert isinstance(result[4], AIMessage)  # ai -> AIMessage
        assert isinstance(result[5], HumanMessage)  # unknown -> HumanMessage (default)

    def test_response_interface(self):
        """Test ResponseInterface class."""
        content = "Test response content"
        response = ResponseInterface(content)

        assert response.content == content
        assert response.to_dict() == {"content": content}

    def test_convert_tools_to_langchain_format_empty(self):
        """Test converting empty tools list."""
        wrapper = LangChainWrapper()
        result = wrapper._convert_tools_to_langchain_format([])

        assert result == []

    def test_convert_tools_to_langchain_format_langchain_tools(self, whatsapp_tools):
        """Test converting LangChain tools (should pass through unchanged)."""
        wrapper = LangChainWrapper()
        tools = whatsapp_tools.get_all_tools()[:3]  # Get first 3 tools

        result = wrapper._convert_tools_to_langchain_format(tools)

        assert len(result) == 3
        assert result == tools  # Should be unchanged

    def test_convert_tools_to_langchain_format_openai_format(self):
        """Test converting OpenAI format tools."""
        wrapper = LangChainWrapper()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "A test function",
                    "parameters": {
                        "type": "object",
                        "properties": {"param1": {"type": "string"}},
                    },
                },
            }
        ]

        result = wrapper._convert_tools_to_langchain_format(tools)

        assert len(result) == 1
        assert result[0] == tools[0]  # Should pass through OpenAI format

    @pytest.mark.parametrize(
        "model_string,expected_provider,expected_model",
        [
            ("openai/gpt-4", "openai", "gpt-4"),
            ("anthropic/claude-3-sonnet", "anthropic", "claude-3-sonnet"),
            ("gemini/gemini-pro", "gemini", "gemini-pro"),
            ("groq/llama-3", "groq", "llama-3"),
            ("fireworks_ai/llama-v2", "fireworks_ai", "llama-v2"),
        ],
    )
    def test_model_string_parsing(
        self, model_string, expected_provider, expected_model
    ):
        """Test parsing model strings into provider and model name."""
        wrapper = LangChainWrapper()

        try:
            provider, model_name = model_string.split("/", 1)
            assert provider == expected_provider
            assert model_name == expected_model
        except ValueError:
            pytest.fail(f"Failed to parse model string: {model_string}")

    def test_invalid_model_format(self):
        """Test handling of invalid model format."""
        wrapper = LangChainWrapper()

        with pytest.raises(Exception) as exc_info:
            wrapper.completion(
                model="invalid_format",  # No slash separator
                messages=[{"role": "user", "content": "test"}],
            )

        assert "Invalid model format" in str(exc_info.value)

    def test_handle_tool_choice_string_values(self):
        """Test handling different tool_choice string values."""
        wrapper = LangChainWrapper()
        mock_model = Mock()

        # Test with "auto"
        result = wrapper._handle_tool_choice(mock_model, "auto")
        assert result == mock_model

        # Test with "none"
        result = wrapper._handle_tool_choice(mock_model, "none")
        assert result == mock_model

        # Test with None
        result = wrapper._handle_tool_choice(mock_model, None)
        assert result == mock_model

    def test_handle_tool_choice_dict_values(self):
        """Test handling tool_choice dictionary values."""
        wrapper = LangChainWrapper()
        mock_model = Mock()

        tool_choice = {"type": "function", "function": {"name": "test_function"}}

        result = wrapper._handle_tool_choice(mock_model, tool_choice)
        assert result == mock_model  # Should return model unchanged

    @patch("agents.utils.langchain_wrapper.OPENAI_API_KEY", "test_key")
    def test_get_model_caching(self):
        """Test that model instances are cached properly."""
        wrapper = LangChainWrapper()

        # Mock the ChatOpenAI class to avoid actual API calls
        with patch("agents.utils.langchain_wrapper.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            # First call should create the model
            model1 = wrapper._get_model("openai", "gpt-4")
            assert model1 == mock_instance
            assert mock_chat_openai.call_count == 1

            # Second call should use cached model
            model2 = wrapper._get_model("openai", "gpt-4")
            assert model2 == mock_instance
            assert mock_chat_openai.call_count == 1  # Should not be called again

            # Different model should create new instance
            model3 = wrapper._get_model("openai", "gpt-3.5-turbo")
            assert model3 == mock_instance
            assert mock_chat_openai.call_count == 2

    def test_get_model_unsupported_provider(self):
        """Test handling of unsupported provider."""
        wrapper = LangChainWrapper()

        with pytest.raises(Exception) as exc_info:
            wrapper._get_model("unsupported_provider", "some_model")

        assert "Unsupported provider" in str(exc_info.value)

    @patch("agents.utils.langchain_wrapper.OPENAI_API_KEY", None)
    def test_get_model_missing_api_key(self):
        """Test handling of missing API key."""
        wrapper = LangChainWrapper()

        with pytest.raises(Exception) as exc_info:
            wrapper._get_model("openai", "gpt-4")

        # Should raise an API key exception
        assert "API key" in str(exc_info.value) or "OpenAI" in str(exc_info.value)

    def test_handle_json_response_valid_json(self):
        """Test handling JSON response with valid JSON content."""
        wrapper = LangChainWrapper()
        mock_response = Mock()
        mock_response.content = '{"message": "Hello", "type": "greeting"}'

        result = wrapper._handle_json_response(mock_response, "openai")

        assert isinstance(result, ResponseInterface)
        parsed_content = json.loads(result.content)
        assert parsed_content["message"] == "Hello"
        assert parsed_content["type"] == "greeting"

    def test_handle_json_response_invalid_json(self):
        """Test handling JSON response with invalid JSON content."""
        wrapper = LangChainWrapper()
        mock_response = Mock()
        mock_response.content = "This is not JSON content"

        result = wrapper._handle_json_response(mock_response, "openai")

        assert isinstance(result, ResponseInterface)
        # Should return empty JSON object as fallback
        assert result.content == "{}"

    def test_handle_json_response_partial_json(self):
        """Test handling JSON response with partial JSON in content."""
        wrapper = LangChainWrapper()
        mock_response = Mock()
        mock_response.content = 'Here is the response: {"status": "success", "data": "test"} and some more text'
        result = wrapper._handle_json_response(mock_response, "openai")

        assert isinstance(result, ResponseInterface)
        parsed_content = json.loads(result.content)
        assert parsed_content["status"] == "success"
        assert parsed_content["data"] == "test"

    def test_handle_streaming_response(self):
        """Test handling streaming response."""
        wrapper = LangChainWrapper()
        mock_model = Mock()

        # Mock streaming chunks
        mock_chunks = [Mock(content="Hello"), Mock(content=" world"), Mock(content="!")]
        mock_model.stream.return_value = mock_chunks

        messages = [HumanMessage(content="test")]

        result = list(wrapper._handle_streaming(mock_model, messages))

        assert len(result) == 3
        assert result[0]["type"] == "content_block_delta"
        assert result[0]["delta"] == "Hello"
        assert result[1]["delta"] == " world"
        assert result[2]["delta"] == "!"

    def test_handle_tool_response(self):
        """Test handling response with tool calls."""
        wrapper = LangChainWrapper()
        mock_response = Mock()
        mock_response.content = "I'll help you with that."

        # Mock tool calls
        mock_tool_call = {"name": "test_function", "args": {"param1": "value1"}}
        mock_response.tool_calls = [mock_tool_call]

        result = wrapper._handle_tool_response(mock_response, "openai")

        assert isinstance(result, ResponseInterface)
        parsed_content = json.loads(result.content)
        assert parsed_content["content"] == "I'll help you with that."
        assert len(parsed_content["tool_calls"]) == 1
        assert parsed_content["tool_calls"][0]["function"]["name"] == "test_function"


class TestReActFunctionality:
    """Test class for ReAct agent functionality."""

    def test_handle_tool_choice_react(self):
        """Test that tool_choice='react' is handled correctly."""
        wrapper = LangChainWrapper()
        mock_model = Mock()

        result = wrapper._handle_tool_choice(mock_model, "react")
        assert result == mock_model

    def test_execute_tool_calls_with_invoke(self):
        """Test executing tool calls with invoke method."""
        wrapper = LangChainWrapper()

        # Mock tool with invoke method
        mock_tool = Mock()
        mock_tool.invoke.return_value = "Tool executed successfully"

        tools_map = {"test_tool": mock_tool}
        tool_calls = [
            {"name": "test_tool", "args": {"param1": "value1"}, "id": "call_123"}
        ]

        result = wrapper._execute_tool_calls(tool_calls, tools_map)

        assert len(result) == 1
        assert result[0].content == "Tool executed successfully"
        assert result[0].tool_call_id == "call_123"
        mock_tool.invoke.assert_called_once_with({"param1": "value1"})

    def test_execute_tool_calls_with_run(self):
        """Test executing tool calls with run method."""
        wrapper = LangChainWrapper()

        # Mock tool with run method
        mock_tool = Mock()
        mock_tool.run.return_value = "Tool ran successfully"
        mock_tool.invoke = Mock(side_effect=AttributeError)  # Make invoke fail

        tools_map = {"test_tool": mock_tool}
        tool_calls = [
            {"name": "test_tool", "args": {"param1": "value1"}, "id": "call_456"}
        ]

        result = wrapper._execute_tool_calls(tool_calls, tools_map)

        assert len(result) == 1
        assert result[0].content == "Tool ran successfully"
        assert result[0].tool_call_id == "call_456"

    def test_execute_tool_calls_callable_tool(self):
        """Test executing tool calls with callable tool."""
        wrapper = LangChainWrapper()

        # Mock callable tool
        def mock_tool(**kwargs):
            return f"Called with {kwargs}"

        tools_map = {"test_tool": mock_tool}
        tool_calls = [
            {"name": "test_tool", "args": {"param1": "value1"}, "id": "call_789"}
        ]

        result = wrapper._execute_tool_calls(tool_calls, tools_map)

        assert len(result) == 1
        assert "Called with {'param1': 'value1'}" in result[0].content
        assert result[0].tool_call_id == "call_789"

    def test_execute_tool_calls_tool_not_found(self):
        """Test executing tool calls when tool is not found."""
        wrapper = LangChainWrapper()

        tools_map = {}  # Empty tools map
        tool_calls = [
            {"name": "nonexistent_tool", "args": {"param1": "value1"}, "id": "call_999"}
        ]

        result = wrapper._execute_tool_calls(tool_calls, tools_map)

        assert len(result) == 1
        assert "Tool 'nonexistent_tool' not found" in result[0].content
        assert result[0].tool_call_id == "call_999"

    def test_execute_tool_calls_tool_error(self):
        """Test executing tool calls when tool raises an error."""
        wrapper = LangChainWrapper()

        # Mock tool that raises an error
        mock_tool = Mock()
        mock_tool.invoke.side_effect = Exception("Tool execution failed")

        tools_map = {"error_tool": mock_tool}
        tool_calls = [
            {"name": "error_tool", "args": {"param1": "value1"}, "id": "call_error"}
        ]

        result = wrapper._execute_tool_calls(tool_calls, tools_map)

        assert len(result) == 1
        assert "Error executing tool: Tool execution failed" in result[0].content
        assert result[0].tool_call_id == "call_error"

    @patch("agents.utils.langchain_wrapper.OPENAI_API_KEY", "test_key")
    def test_handle_react_completion_single_iteration(self):
        """Test ReAct completion that resolves in one iteration (no tool calls)."""
        wrapper = LangChainWrapper()

        # Mock model instance
        mock_model = Mock()
        mock_response = Mock()
        mock_response.content = "Final answer without tool calls"
        mock_response.tool_calls = []  # No tool calls
        mock_model.invoke.return_value = mock_response

        messages = [HumanMessage(content="Test message")]
        tools_map = {}

        result = wrapper._handle_react_completion(
            mock_model, messages, tools_map, "openai", False
        )

        assert isinstance(result, ResponseInterface)
        assert result.content == "Final answer without tool calls"
        assert mock_model.invoke.call_count == 1

    @patch("agents.utils.langchain_wrapper.OPENAI_API_KEY", "test_key")
    def test_handle_react_completion_multiple_iterations(self):
        """Test ReAct completion that requires multiple iterations with tool calls."""
        wrapper = LangChainWrapper()

        # Mock tool
        mock_tool = Mock()
        mock_tool.invoke.return_value = "Tool result: 42"
        tools_map = {"calculator": mock_tool}

        # Mock model responses
        mock_model = Mock()

        # First response: with tool call
        first_response = Mock()
        first_response.content = "I need to calculate something"
        first_response.tool_calls = [
            {
                "name": "calculator",
                "args": {"operation": "add", "a": 20, "b": 22},
                "id": "call_calc1",
            }
        ]

        # Second response: final answer
        second_response = Mock()
        second_response.content = "The answer is 42"
        second_response.tool_calls = []  # No more tool calls

        mock_model.invoke.side_effect = [first_response, second_response]

        messages = [HumanMessage(content="What is 20 + 22?")]

        result = wrapper._handle_react_completion(
            mock_model, messages, tools_map, "openai", False
        )

        assert isinstance(result, ResponseInterface)
        assert result.content == "The answer is 42"
        assert mock_model.invoke.call_count == 2
        assert mock_tool.invoke.call_count == 1

    @patch("agents.utils.langchain_wrapper.OPENAI_API_KEY", "test_key")
    def test_handle_react_completion_max_iterations(self):
        """Test ReAct completion reaches max iterations."""
        wrapper = LangChainWrapper()

        # Mock tool
        mock_tool = Mock()
        mock_tool.invoke.return_value = "Tool result"
        tools_map = {"test_tool": mock_tool}

        # Mock model that always returns tool calls
        mock_model = Mock()
        mock_response = Mock()
        mock_response.content = "Need more tools"
        mock_response.tool_calls = [
            {"name": "test_tool", "args": {}, "id": "call_test"}
        ]
        mock_model.invoke.return_value = mock_response

        messages = [HumanMessage(content="Test message")]

        # Set max_iterations to 2 for quick test
        result = wrapper._handle_react_completion(
            mock_model, messages, tools_map, "openai", False, max_iterations=2
        )

        assert isinstance(result, ResponseInterface)
        assert result.content == "Need more tools"  # Should return last response
        assert mock_model.invoke.call_count == 2  # Should hit max iterations
