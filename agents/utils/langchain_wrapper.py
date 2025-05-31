import json
import re
import time
from typing import Any, Dict, List, Union

from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatFireworks
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from agents.constants.tenant_maps import (
    ANTHROPIC_API_KEY,
    FIREWORKS_API_KEY,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OPENAI_API_KEY,
)
from agents.utils.langfuse_utils import with_langfuse_tracing
from constants.exceptions import Exceptions
from helpers.index import get_json_from_response
from helpers.logger_config import logger


def get_clean_messages(messages: List[Dict]) -> List[Dict]:
    """Clean and validate messages for LLM consumption."""
    clean_messages = []

    for msg in messages:
        if not isinstance(msg, dict):
            logger.warning(
                "Invalid message format, skipping", data={"message": str(msg)}
            )
            continue

        # Ensure required fields exist
        if "role" not in msg or "content" not in msg:
            logger.warning("Message missing required fields", data={"message": msg})
            continue

        # Clean the message
        clean_msg = {"role": msg["role"], "content": msg["content"]}

        # Handle additional fields if present
        if "name" in msg:
            clean_msg["name"] = msg["name"]

        clean_messages.append(clean_msg)

    return clean_messages


def convert_to_langchain_messages(
    messages: List[Dict],
) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
    """Convert dictionary messages to LangChain message objects."""
    langchain_messages = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "user" or role == "human":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant" or role == "ai":
            langchain_messages.append(AIMessage(content=content))
        else:
            # Default to human message
            langchain_messages.append(HumanMessage(content=content))

    return langchain_messages


class ResponseInterface:
    def __init__(self, content: str):
        self.content = content

    def to_dict(self):
        return {
            "content": self.content,
        }


class LangChainWrapper:
    def __init__(
        self,
        workflow_name: str = "",
    ):
        self.workflow_name = workflow_name
        self._models = {}  # Cache for model instances

    def _get_model(self, provider: str, model_name: str, **kwargs) -> Any:
        """Get or create a model instance for the given provider."""
        cache_key = f"{provider}:{model_name}"

        if cache_key not in self._models:
            if provider == "openai":
                if not OPENAI_API_KEY:
                    raise Exceptions.api_key_exception("OpenAI")
                self._models[cache_key] = ChatOpenAI(
                    model=model_name,
                    api_key=OPENAI_API_KEY,
                    temperature=kwargs.get("temperature", 0.7),
                    **kwargs,
                )
            elif provider == "anthropic":
                if not ANTHROPIC_API_KEY:
                    raise Exceptions.api_key_exception("Anthropic")
                self._models[cache_key] = ChatAnthropic(
                    model=model_name,
                    api_key=ANTHROPIC_API_KEY,
                    temperature=kwargs.get("temperature", 0.7),
                    **kwargs,
                )
            elif provider == "gemini":
                if not GEMINI_API_KEY:
                    raise Exceptions.api_key_exception("Gemini")
                self._models[cache_key] = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=GEMINI_API_KEY,
                    temperature=kwargs.get("temperature", 0.7),
                    **kwargs,
                )
            elif provider == "groq":
                if not GROQ_API_KEY:
                    raise Exceptions.api_key_exception("Groq")
                self._models[cache_key] = ChatGroq(
                    model=model_name,
                    api_key=GROQ_API_KEY,
                    temperature=kwargs.get("temperature", 0.7),
                    **kwargs,
                )
            elif provider == "fireworks_ai":
                if not FIREWORKS_API_KEY:
                    raise Exceptions.api_key_exception("Fireworks")
                self._models[cache_key] = ChatFireworks(
                    model=model_name,
                    api_key=FIREWORKS_API_KEY,
                    temperature=kwargs.get("temperature", 0.7),
                    **kwargs,
                )
            else:
                raise Exceptions.general_exception(
                    400, f"Unsupported provider: {provider}"
                )

        return self._models[cache_key]

    def _convert_tools_to_langchain_format(self, tools: List) -> List:
        """Convert tools from various formats to LangChain format if needed."""
        if not tools:
            return []

        langchain_tools = []
        for tool in tools:
            # If it's already a LangChain tool object (has __call__ method), use it directly
            if callable(tool) and hasattr(tool, "name"):
                langchain_tools.append(tool)
            elif isinstance(tool, dict):
                # If it's a dictionary in OpenAI format, use it as is
                if "type" in tool and tool["type"] == "function":
                    langchain_tools.append(tool)
                else:
                    # Convert if needed
                    langchain_tools.append(tool)
            else:
                # Try to use it directly
                langchain_tools.append(tool)

        return langchain_tools

    def _execute_tool_calls(
        self, tool_calls, tools_map: Dict, user_id: str
    ) -> List[ToolMessage]:
        """Execute tool calls and return tool messages."""
        tool_messages = []
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                if "user_id" in tool_args:
                    tool_args["user_id"] = user_id
                if "userId" in tool_args:
                    tool_args["userId"] = user_id
                logger.debug(f"tool_args: {tool_args}")
                tool_id = tool_call.get("id", f"call_{int(time.time())}")

                if tool_name in tools_map:
                    tool = tools_map[tool_name]
                    # Execute the tool
                    result = None
                    if hasattr(tool, "invoke"):
                        try:
                            result = tool.invoke(tool_args)
                        except AttributeError:
                            # invoke method exists but fails, try other methods
                            pass

                    if result is None and hasattr(tool, "run"):
                        result = tool.run(tool_args)
                    elif result is None and hasattr(tool, "_run"):
                        result = tool._run(tool_args)
                    elif result is None and callable(tool):
                        result = tool(**tool_args)
                    elif (
                        result is None and isinstance(tool, dict) and "function" in tool
                    ):
                        # Handle OpenAI format tools - these would need custom execution logic
                        result = f"OpenAI format tool {tool_name} requires custom execution logic"
                    elif result is None:
                        result = f"Tool {tool_name} is not callable"

                    # Create tool message
                    tool_message = ToolMessage(
                        content=str(result), tool_call_id=tool_id
                    )
                    tool_messages.append(tool_message)
                else:
                    # Tool not found
                    tool_message = ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found",
                        tool_call_id=tool_id,
                    )
                    tool_messages.append(tool_message)
            except Exception as e:
                logger.error(
                    f"Error executing tool {tool_call.get('name', 'unknown')}",
                    error=str(e),
                )
                tool_message = ToolMessage(
                    content=f"Error executing tool: {str(e)}",
                    tool_call_id=tool_call.get("id", f"call_{int(time.time())}"),
                )
                tool_messages.append(tool_message)
        return tool_messages

    def _handle_react_completion(
        self,
        model_instance,
        messages,
        user_id: str,
        tools_map: Dict,
        provider: str,
        json_flag: bool,
        max_iterations: int = 10,
    ) -> ResponseInterface:
        """Handle ReAct agent completion with tool calling recursion."""
        current_messages = messages.copy()
        iteration = 0

        while iteration < max_iterations:
            try:
                logger.debug(
                    f"ReAct iteration {iteration + 1}: Making LLM call",
                    data={"messages": current_messages, "user_id": user_id},
                )
                response = model_instance.invoke(current_messages)
                if hasattr(response, "tool_calls") and response.tool_calls:
                    logger.debug(
                        f"ReAct iteration {iteration + 1}: Tool calls found",
                        data={
                            "tool_calls": [
                                tc.get("name", "") for tc in response.tool_calls
                            ]
                        },
                    )
                    current_messages.append(response)
                    tool_messages = self._execute_tool_calls(
                        response.tool_calls, tools_map, user_id
                    )
                    current_messages.extend(tool_messages)
                    iteration += 1
                    continue
                else:
                    logger.debug(f"ReAct completed after {iteration + 1} iterations")
                    if json_flag:
                        return self._handle_json_response(response, provider)
                    else:
                        return ResponseInterface(content=response.content)

            except Exception as e:
                logger.error(f"Error in ReAct iteration {iteration + 1}", error=str(e))
                # Return current response or error
                if "response" in locals():
                    return ResponseInterface(
                        content=response.content or f"Error in ReAct: {str(e)}"
                    )
                else:
                    raise Exceptions.general_exception(
                        500, f"Error in ReAct completion: {str(e)}"
                    )

        # Max iterations reached
        logger.warning(f"ReAct agent reached max iterations ({max_iterations})")
        if "response" in locals():
            if json_flag:
                return self._handle_json_response(response, provider)
            else:
                return ResponseInterface(content=response.content)
        else:
            return ResponseInterface(
                content="ReAct agent reached maximum iterations without a final response"
            )

    def _handle_tool_choice(self, model_instance, tool_choice: str):
        """Handle tool choice configuration for different providers."""
        if not tool_choice:
            return model_instance

        # LangChain handles tool_choice differently than OpenAI
        # For most providers, we can pass it through or adapt as needed
        try:
            if isinstance(tool_choice, str):
                # Handle string values like "auto", "none", "react"
                if tool_choice == "auto":
                    return model_instance  # Default behavior
                elif tool_choice == "none":
                    return model_instance  # No specific handling needed
                elif tool_choice == "react":
                    # ReAct mode uses auto tool calling but with recursion
                    return model_instance
            elif isinstance(tool_choice, dict):
                # Handle specific function choices
                if tool_choice.get("type") == "function":
                    # Some providers support specific function selection
                    return model_instance
        except Exception as e:
            logger.warning(f"Could not apply tool_choice: {e}")

        return model_instance

    def completion(
        self,
        model: str,
        messages: List[Dict],
        json_flag: bool = False,
        session_id: str = "",
        user_id: str = "",
        stream: bool = False,
        search_bool: bool = False,
        tools: List[Dict] = None,
        tool_choice: str = None,
    ) -> Any:
        """
        Main completion method that routes to appropriate provider.

        Args:
            model: Model name in format "provider/model_name"
            messages: List of conversation messages
            json_flag: Whether to parse response as JSON
            session_id: Session identifier for tracing
            user_id: User identifier for tracing
            stream: Whether to stream the response
            search_bool: Whether this is a search operation
            tools: List of tools available to the model
            tool_choice: How tools should be used:
                - "auto": Model decides when to use tools (default)
                - "none": Never use tools
                - "react": ReAct agent mode - automatically execute tools and recurse until final answer

        Returns:
            ResponseInterface object with the completion result

        Note:
            When tool_choice="react", the agent will:
            1. Make an LLM call
            2. If tool calls are present, execute them and add results to conversation
            3. Repeat until LLM responds without tool calls
            4. Return the final response
        """
        logger.debug(f"Reaching here isnide completion {user_id}")
        try:
            provider, model_name = model.split("/", 1)
        except ValueError:
            raise Exceptions.general_exception(
                400, f"Invalid model format. Expected 'provider/model', got: {model}"
            )

        clean_messages = get_clean_messages(messages)
        langchain_messages = convert_to_langchain_messages(clean_messages)

        try:
            model_instance = self._get_model(provider, model_name)
            converted_tools = []
            tools_map = {}
            if tools:
                converted_tools = self._convert_tools_to_langchain_format(tools)
                model_instance = model_instance.bind_tools(converted_tools)

                # Create tools map for ReAct functionality
                for tool in tools:
                    if hasattr(tool, "name"):
                        tools_map[tool.name] = tool
                    elif isinstance(tool, dict):
                        if "function" in tool:
                            # Handle OpenAI format tools
                            func_name = tool["function"].get("name", "")
                            if func_name:
                                tools_map[func_name] = tool
                        elif "name" in tool:
                            # Handle dict with name directly
                            tools_map[tool["name"]] = tool

                # Handle tool choice
                if tool_choice:
                    model_instance = self._handle_tool_choice(
                        model_instance, tool_choice
                    )

            def make_completion_call():
                try:
                    if stream:
                        return self._handle_streaming(
                            model_instance, langchain_messages
                        )
                    else:
                        # Check if ReAct mode is enabled
                        is_react_mode = tool_choice == "react" and tools

                        if is_react_mode:
                            return self._handle_react_completion(
                                model_instance,
                                langchain_messages,
                                user_id,
                                tools_map,
                                provider,
                                json_flag,
                            )
                        else:
                            response = model_instance.invoke(langchain_messages)

                            # Handle tool calls in response
                            if hasattr(response, "tool_calls") and response.tool_calls:
                                # Return response with tool calls
                                return self._handle_tool_response(response, provider)
                            elif json_flag:
                                return self._handle_json_response(response, provider)
                            else:
                                return ResponseInterface(content=response.content)

                except Exception as e:
                    logger.error(f"Error in {provider} completion", error=str(e))
                    raise Exceptions.general_exception(
                        500, f"Error in {provider} completion: {str(e)}"
                    )

            # Use langfuse tracing if available
            return with_langfuse_tracing(
                trace_name=f"{provider}_completion",
                model_name=model_name,
                session_id=session_id,
                user_id=user_id,
                input_data={"messages": clean_messages},
                model_params={
                    "json_flag": json_flag,
                    "stream": stream,
                    "tools": bool(tools),
                },
                api_call=make_completion_call,
            )

        except Exception as e:
            if isinstance(e, HTTPException):
                raise Exceptions.general_exception(e.status_code, str(e.detail))
            raise Exceptions.general_exception(
                500, f"Error in LangChain completion: {str(e)}"
            )

    def _handle_streaming(self, model_instance, messages):
        """Handle streaming responses."""
        for chunk in model_instance.stream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield {
                    "type": "content_block_delta",
                    "delta": chunk.content,
                }

    def _handle_tool_response(self, response, provider: str) -> ResponseInterface:
        """Handle responses that contain tool calls."""
        try:
            # Create a response that includes both content and tool calls
            response_data = {"content": response.content or "", "tool_calls": []}

            if hasattr(response, "tool_calls") and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_call_data = {
                        "id": getattr(tool_call, "id", f"call_{int(time.time())}"),
                        "type": "function",
                        "function": {
                            "name": tool_call.get("name", ""),
                            "arguments": json.dumps(tool_call.get("args", {})),
                        },
                    }
                    response_data["tool_calls"].append(tool_call_data)

            return ResponseInterface(content=json.dumps(response_data))

        except Exception as e:
            logger.error(f"Error handling tool response from {provider}", error=str(e))
            # Fallback to regular content response
            return ResponseInterface(content=response.content or "")

    def _handle_json_response(self, response, provider: str) -> ResponseInterface:
        """Handle JSON response formatting."""
        content = response.content

        try:
            # First, try to directly parse the response as JSON
            json_data = json.loads(content.strip())
            return ResponseInterface(content=json.dumps(json_data))
        except json.JSONDecodeError:
            # If direct parsing fails, try extraction
            json_data = get_json_from_response(content)
            if json_data:
                return ResponseInterface(content=json.dumps(json_data))
            else:
                # Last resort: try to extract anything that looks like JSON
                json_match = re.search(r"({[\s\S]*})", content)
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(1).strip())
                        return ResponseInterface(content=json.dumps(json_data))
                    except:
                        pass

                # If all extraction attempts fail, return an empty object
                logger.warning(
                    f"Could not extract JSON from {provider} response",
                    data={"content": content},
                )
                return ResponseInterface(content="{}")

    def embedding(
        self,
        model: str,
        input_data: List[str],
        user_id: str = "",
        session_id: str = "",
    ) -> Any:
        """Handle embedding requests."""
        try:
            provider, model_name = model.split("/", 1)
        except ValueError:
            raise Exceptions.general_exception(
                400, f"Invalid model format. Expected 'provider/model', got: {model}"
            )

        if provider == "openai":
            if not OPENAI_API_KEY:
                raise Exceptions.api_key_exception("OpenAI")

            def make_embedding_call():
                embeddings = OpenAIEmbeddings(model=model_name, api_key=OPENAI_API_KEY)
                return embeddings.embed_documents(input_data)

            return with_langfuse_tracing(
                trace_name="openai_embedding",
                model_name=model_name,
                session_id=session_id,
                user_id=user_id,
                input_data={"input": input_data},
                api_call=make_embedding_call,
            )
        else:
            raise Exceptions.general_exception(
                400, f"Embedding not supported for provider: {provider}"
            )


def LangChainCompletion(
    model: str,
    messages: List[Dict],
    json_flag: bool = False,
    session_id: str = "",
    workflowName: str = "",
    userId: str = "",
    use_advanced: bool = False,
    search_bool: bool = False,
    tools: List[Dict] = None,
    tool_choice: Dict = None,
) -> Any:
    """
    Main completion function that maintains compatibility with LiteLLM interface.

    Supports ReAct agent functionality when tool_choice="react".
    In ReAct mode, the agent will automatically execute tools and continue
    the conversation until a final answer is reached.
    """
    wrapper = LangChainWrapper(workflow_name=workflowName)

    return wrapper.completion(
        model=model,
        messages=messages,
        json_flag=json_flag,
        session_id=session_id,
        user_id=userId,
        search_bool=search_bool,
        tools=tools,
        tool_choice=tool_choice,
    )


def LangChainEmbedding(
    model: str,
    input_data: List[str],
    user_id: str = "",
    session_id: str = "",
) -> Any:
    """Main embedding function that maintains compatibility with LiteLLM interface."""
    wrapper = LangChainWrapper()

    return wrapper.embedding(
        model=model,
        input_data=input_data,
        user_id=user_id,
        session_id=session_id,
    )
