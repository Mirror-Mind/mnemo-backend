from typing import Dict, Optional, Type, Union

from langgraph.checkpoint.base import BaseCheckpointSaver

from agents.constants.workflow_names import WHATSAPP_WORKFLOW
from agents.workflows.base_workflow import WorkflowInterface
from agents.workflows.whatsapp.index import WhatsAppWorkflow
from constants.exceptions import Exceptions
from helpers.langfuse_config import get_langfuse_callback_handler


class WorkflowOrchestrator:
    def __init__(self, checkpointer: BaseCheckpointSaver):
        self.langfuse_handler = get_langfuse_callback_handler()
        self.WhatsappWorkflow = WhatsAppWorkflow(checkpointer)
        self.agents: Dict[str, Type[WorkflowInterface]] = {
            WHATSAPP_WORKFLOW: self.WhatsappWorkflow,
        }

    def start(
        self, workflow_name: str, message: Optional[Union[dict, str]] = None, **kwargs
    ):
        """Starts a workflow by name if available, else raises an Exceptions."""
        if workflow_name not in self.agents:
            raise Exceptions.not_found_exception("Workflow")
        if message:
            return self.agents[workflow_name].start(message, kwargs=kwargs)
        return self.agents[workflow_name].start(kwargs=kwargs)

    def chat(self, workflow_name: str, thread_id: str, message_dict: dict, **kwargs):
        """Replies to an active workflow given a workflow name, thread ID, and message_dict."""
        if workflow_name not in self.agents:
            raise Exceptions.not_found_exception("Workflow")
        design_variables = {}
        if "design_variables" in message_dict:
            design_variables = message_dict.pop("design_variables")

        kwargs["design_variables"] = design_variables
        return self.agents[workflow_name].chat(thread_id, message_dict, kwargs=kwargs)

    def get_state(self, workflow_name: str, thread_id: str):
        """Retrieves the current state of an active workflow."""
        if workflow_name not in self.agents:
            raise Exceptions.not_found_exception("Workflow")
        return self.agents[workflow_name].get_state(thread_id)

    def resume_workflow(self, workflow_name: str, thread_id: str, message: dict):
        """Resumes an active workflow given a workflow name, thread ID, and message."""
        if workflow_name not in self.agents:
            raise Exceptions.not_found_exception("Workflow")
        return self.agents[workflow_name].resume_workflow(thread_id, message)

    def start_stream_workflow(
        self, workflow_name: str, message: Optional[Union[dict, str]] = None, **kwargs
    ):
        """Starts a workflow by name if available, else raises an Exception."""
        if workflow_name not in self.agents:
            raise Exceptions.not_found_exception("Workflow")
        if message:
            return self.agents[workflow_name].start_stream(message, kwargs=kwargs)
        return self.agents[workflow_name].start_stream(kwargs=kwargs)

    def chat_stream_workflow(self, workflow_name: str, thread_id: str, message: dict):
        """Replies to an active workflow given a workflow name, thread ID, and message."""
        if workflow_name not in self.agents:
            raise Exceptions.not_found_exception("Workflow")
        yield self.agents[workflow_name].chat_stream(thread_id, message)

    def get_workflow_instance(self, workflow_name: str):
        """Retrieves the current state of an active workflow."""
        if workflow_name not in self.agents:
            raise Exceptions.not_found_exception("Workflow")
        return self.agents[workflow_name].get_workflow_instance()
