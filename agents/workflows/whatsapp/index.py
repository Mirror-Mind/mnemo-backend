"""
WhatsApp workflow implementation using LangGraph.
"""

import os
from typing import Dict, List

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.pregel import Pregel
from langsmith.run_helpers import traceable

from agents.constants.workflow_names import WHATSAPP_WORKFLOW
from agents.workflows.base_workflow import WorkflowInterface
from agents.workflows.whatsapp.nodes import WhatsAppNodes
from agents.workflows.whatsapp.state import WhatsAppWorkflowState
from helpers.langfuse_config import get_langfuse_callback_handler


class WhatsAppWorkflow(WorkflowInterface):
    """WhatsApp workflow for processing messages and generating responses."""

    def __init__(self, Checkpointer: BaseCheckpointSaver):
        """Initialize the WhatsApp workflow."""
        self.workflow_name = WHATSAPP_WORKFLOW
        self.graph = StateGraph(WhatsAppWorkflowState)
        self.whatsapp_nodes = WhatsAppNodes(workflow_name=self.workflow_name)
        self._initialize_graph()

        self.workflow_instance = self.graph.compile(
            checkpointer=Checkpointer,
            interrupt_before=["buffer_node"],
            interrupt_after=[],
        ).with_config(recursion_limit=100)

        self._save_workflow_diagram(os.path.dirname(__file__))

        self.initial_message = BaseMessage(
            content="Hi, I'm your WhatsApp assistant",
            type="text",
            role="system",
        )

        self.initial_state = WhatsAppWorkflowState(
            messages=[],
            user_id="",
            phone_number="",
            whatsapp_message_id=None,
            user_details=None,
            memory_context=None,
            response_type="text",
            response_content={},
            stepper={},
            finished=False,
            session_id="",
            stream=False,
            is_processing=False,
            error=None,
        )

        self.langfuse_handler = get_langfuse_callback_handler(
            metadata={"workflow": self.workflow_name},
            tags=["workflow", self.workflow_name],
        )

    def _initialize_graph(self):
        """Initialize the workflow graph with nodes and edges."""
        # Add nodes
        self.graph.add_node(
            "process_message_node", self.whatsapp_nodes.process_message_node
        )
        self.graph.add_node(
            "generate_response_node", self.whatsapp_nodes.generate_response_node
        )
        self.graph.add_node("buffer_node", self.whatsapp_nodes.buffer_node)

        # Add edges
        self.graph.add_edge(START, "process_message_node")
        self.graph.add_edge("process_message_node", "generate_response_node")
        self.graph.add_edge("generate_response_node", "buffer_node")
        self.graph.add_conditional_edges(
            "buffer_node",
            lambda state: str(state.get("finished", False)),
            {"True": END, "False": "process_message_node"},
        )

    @traceable(run_type="chain")
    def invoke(
        self, inputs: Dict, config: Dict, stream_output: bool = False
    ) -> Pregel | List[BaseMessage]:
        """Invoke the workflow with inputs."""
        if stream_output:
            return self.workflow_instance.stream(
                input=inputs,
                config=config,
            )
        return self.workflow_instance.invoke(
            input=inputs,
            config=config,
        )

    def get_state(self, config: Dict) -> WhatsAppWorkflowState:
        """Get the current state of the workflow."""
        return self.workflow_instance.get_state(config=config)

    def update_state(self, config: Dict, values: Dict) -> CompiledGraph:
        """Update the workflow state."""
        return self.workflow_instance.update_state(config=config, values=values)
