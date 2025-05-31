"""
WhatsApp workflow state definition.
"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage

from agents.workflows.base_workflow import BaseWorkflowState


class WhatsAppWorkflowState(BaseWorkflowState):
    """State for WhatsApp workflow."""

    messages: List[BaseMessage]
    user_id: str
    phone_number: str
    whatsapp_message_id: Optional[str]
    memory_context: Optional[str]
    response_type: str  # "text", "interactive_buttons", "interactive_list"
    response_content: Dict[str, Any]
    stepper: Dict[str, Any]
    stream: bool
    is_processing: bool
    error: Optional[str]
    session_id: str
    finished: bool
