"""
WhatsApp workflow nodes for processing messages and generating responses.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from langchain_core.messages import AIMessage

from agents.utils.langchain_wrapper import LangChainWrapper
from helpers.logger_config import logger

# Import the validation function from helpers
from helpers.whatsapp_validator import validate_and_fix_whatsapp_message

from .memory import WhatsAppMemoryManager
from .prompts import AGENT_SYSTEM_PROMPT, WHATSAPP_SYSTEM_PROMPT
from .tools import WhatsAppTools


class WhatsAppNodes:
    """Nodes for WhatsApp workflow processing."""

    def __init__(self, workflow_name: str):
        """Initialize WhatsApp nodes with tools and models."""
        self.workflow_name = workflow_name
        self.memory_manager = WhatsAppMemoryManager()
        self.tools = WhatsAppTools(memory_manager=self.memory_manager).get_all_tools()
        self.llm_wrapper = LangChainWrapper(workflow_name=workflow_name)
        self.model_name = "openai/gpt-4.1-mini-2025-04-14"

    def process_message_node(self, state) -> Dict[str, Any]:
        """Process incoming WhatsApp message and prepare for AI response."""
        try:
            logger.info(
                "Processing WhatsApp message",
                data={
                    "user_id": state.get("user_id"),
                    "phone_number": state.get("phone_number"),
                },
            )
            messages = state.get("messages", [])
            if not messages:
                return {
                    "error": "No messages to process",
                }
            user_message = messages[-1]
            user_id = state.get("user_id")
            memory_context = ""
            if user_message.content:
                logger.info("Searching memories", data={"user_id": user_id})
                memory_results = self.memory_manager.search_memories(
                    str(user_message.content), user_id, limit=5
                )
                logger.debug("Memory results", data={"memory_results": memory_results})
                if memory_results:
                    relevant_memories = [
                        result.get("memory", str(result)) for result in memory_results
                    ]
                    memory_context = "\n".join(relevant_memories)
            updated_state = {
                "memory_context": memory_context, 
                "is_processing": True,
                "error": None,  # Clear any previous errors on successful processing
            }
            logger.info(
                "Message processed successfully",
                data={"user_id": user_id, "has_memory_context": bool(memory_context)},
            )
            return updated_state

        except Exception as e:
            logger.error("Error processing message", error=str(e))
            return {
                **state,
                "error": f"Error processing message: {str(e)}",
            }

    def generate_response_node(self, state) -> Dict[str, Any]:
        """Generate AI response using LiteLLM wrapper."""
        try:
            logger.info(
                "Generating AI response", data={"user_id": state.get("user_id")}
            )
            messages = state.get("messages", [])
            user_id = state.get("user_id")
            memory_context = state.get("memory_context") or ""
            user_details = state.get("user_details", {})
            if not messages:
                return {
                    **state,
                    "error": "No messages to generate response for",
                }
            # Prepare system message with context
            current_time = (
                datetime.now(timezone.utc)
                .astimezone(timezone(timedelta(hours=5, minutes=30)))
                .isoformat()
            )
            system_content = f"{AGENT_SYSTEM_PROMPT}\n\n{WHATSAPP_SYSTEM_PROMPT}\n\n"
            system_content += f"User details: {json.dumps(user_details)}\n\n"
            system_content += f"Current date and time: {current_time}\n\n"
            if memory_context:
                system_content += (
                    f"Previous relevant information:\n{memory_context}\n\n"
                )
            llm_messages = [{"role": "system", "content": system_content}]
            recent_messages = messages[-10:]
            for msg in recent_messages:
                llm_messages.append({"role": "user", "content": str(msg.content)})
            response = self.llm_wrapper.completion(
                model=self.model_name,
                messages=llm_messages,
                json_flag=True,
                session_id=state.get("session_id", "default"),
                user_id=user_id,
                tool_choice="react",
                tools=self.tools,
            )
            if not response or not hasattr(response, "content"):
                return {
                    **state,
                    "error": "No AI response generated",
                }
            response_content = response.content
            try:
                parsed_response = json.loads(response_content)
                response_type = parsed_response.get("message_type", "text")
            except json.JSONDecodeError as e:
                parsed_response = {
                    "message_type": "text",
                    "type": "text",
                    "text": response_content,
                }
                response_type = "text"
            ai_response = AIMessage(content=response_content)
            conversation_messages = [messages[-1], ai_response]
            logger.info("Adding memory", data={"user_id": user_id})
            self.memory_manager.add_memory(
                conversation_messages,
                user_id,
                metadata={"source": "whatsapp", "timestamp": current_time},
            )
            updated_state = {
                **state,
                "messages": messages + [ai_response],
                "response_type": response_type,
                "response_content": parsed_response,
                "is_processing": False,
                "error": None,  # Clear any previous errors on successful response
            }
            logger.info(
                "AI response generated successfully",
                data={
                    "user_id": user_id,
                    "response_type": response_type,
                    "response_content": parsed_response,
                },
            )

            updated_state["response_content"] = self.format_whatsapp_response(
                parsed_response
            )
            return updated_state

        except Exception as e:
            logger.error("Error generating AI response", error=str(e))
            return {
                **state,
                "error": f"Error generating response: {str(e)}",
                "is_processing": False,
            }

    def buffer_node(self, state) -> Dict[str, Any]:
        """Buffer the response for WhatsApp API."""
        return state

    def format_whatsapp_response(
        self, response_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format response for WhatsApp API."""
        try:
            message_type = response_content.get("message_type", "text")

            if message_type == "text":
                payload = {
                    "messaging_product": "whatsapp",
                    "to": "",  # Will be filled by the webhook handler
                    "type": "text",
                    "text": {"body": response_content.get("text", "")},
                }

            elif message_type == "interactive":
                interactive_type = response_content.get("type", "button")

                payload = {
                    "messaging_product": "whatsapp",
                    "to": "",  # Will be filled by the webhook handler
                    "type": "interactive",
                    "interactive": {"type": interactive_type},
                }

                # Add body
                if response_content.get("body"):
                    payload["interactive"]["body"] = response_content["body"]

                # Add header
                if response_content.get("header"):
                    payload["interactive"]["header"] = response_content["header"]

                # Add footer
                if response_content.get("footer"):
                    payload["interactive"]["footer"] = response_content["footer"]

                # Add action
                if response_content.get("action"):
                    payload["interactive"]["action"] = response_content["action"]

            else:
                # Fallback to text
                payload = {
                    "messaging_product": "whatsapp",
                    "to": "",
                    "type": "text",
                    "text": {"body": "I didn't understand that. Please try again."},
                }

            # Validate and fix the payload using the comprehensive validation function
            validated_payload = validate_and_fix_whatsapp_message(payload)
            return validated_payload

        except Exception as e:
            logger.error("Error formatting WhatsApp response", error=str(e))
            return {
                "messaging_product": "whatsapp",
                "to": "",
                "type": "text",
                "text": {"body": "Sorry, I encountered an error. Please try again."},
            }
