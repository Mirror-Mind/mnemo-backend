import os
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.runnables.graph import MermaidDrawMethod
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command

from helpers.index import stripped_uuid4
from helpers.langfuse_config import get_langfuse_callback_handler


class BaseWorkflowState(TypedDict):
    messages: List[BaseMessage]
    stepper: Dict[str, Any]
    finished: bool
    session_id: str
    stream: bool
    is_processing: bool


class WorkflowInterface(ABC):
    """An interface for workflows to standardize structure and behavior."""

    @abstractmethod
    def __init__(self, Checkpointer: BaseCheckpointSaver):
        self.workflow_instance = None
        self.workflow_name = "workflow_name"
        self.initial_state = None
        self.checkpointer = Checkpointer
        self.langfuse_handler = get_langfuse_callback_handler(
            metadata={"workflow": getattr(self, "workflow_name", "undefined_workflow")},
            tags=["workflow", getattr(self, "workflow_name", "undefined_workflow")],
        )

    def _save_workflow_diagram(self, file_path: str):
        try:
            self.mermaidimg = self.workflow_instance.get_graph().draw_mermaid_png(
                draw_method=MermaidDrawMethod.API,
            )
            folder_name = os.path.basename(file_path)
            output_file_path = os.path.join(file_path, f"{folder_name}-diagram.png")
            with open(output_file_path, "wb") as f:
                f.write(self.mermaidimg)
        except Exception:
            pass

    def start(self, message: dict = {}, **kwargs):
        """Start the workflow, returning a thread ID and the initial event."""
        thread_id = stripped_uuid4()
        user_id = kwargs["kwargs"].get("user_id", "")
        self.langfuse_handler = get_langfuse_callback_handler(
            session_id=thread_id,
            user_id=user_id,
            metadata={"workflow": self.workflow_name},
            tags=["workflow", self.workflow_name],
        )
        initial_state = deepcopy(self.initial_state)
        initial_state["session_id"] = thread_id
        initial_state["stream"] = False
        initial_state["is_processing"] = True
        if kwargs:
            for key, value in kwargs["kwargs"].items():
                initial_state[key] = value
        if (
            len(initial_state.get("messages", [])) == 0
            and not message
            and self.initial_message
        ):
            initial_state["messages"].append(self.initial_message)
        callbacks = [self.langfuse_handler] if self.langfuse_handler else []
        config: RunnableConfig = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "user_id": user_id,
            },
            callbacks=callbacks,
        )
        if message:
            initial_message = BaseMessage(
                content=message.get("content", ""),
                type=message.get("type", "text"),
                role=message.get("role", "user"),
                file=message.get("file", ""),
                image=message.get("image", ""),
            )
            initial_state["messages"].append(initial_message)
            latest_event = None
            latest_update = None
            for event in self.workflow_instance.stream(
                initial_state, config, stream_mode=["values", "updates"]
            ):
                if event[0] == "updates":
                    latest_update = event
                else:
                    latest_event = event
            # Set is_processing to False before returning
            if latest_event and latest_event[1]:
                latest_event[1]["is_processing"] = False
                self.workflow_instance.update_state(
                    config=config, values=latest_event[1]
                )

            if latest_update is not None:
                interrupt = latest_update[1].get("__interrupt__")
                if interrupt:
                    return (
                        thread_id,
                        latest_event[1],
                        "node_interrupt",
                        interrupt[0].value,
                    )
            return thread_id, latest_event[1], "workflow_interrupt", ""
        else:
            self.workflow_instance.update_state(config=config, values=initial_state)
            # Set is_processing to False after initial state update
            initial_state["is_processing"] = False
            self.workflow_instance.update_state(config=config, values=initial_state)
            return thread_id, initial_state, "initial_event", ""

    def chat(self, thread_id: str, message: dict, file: Optional[str] = None, **kwargs):
        """Handle a chat within the workflow, updating its state and returning the latest event."""
        # First get state with basic config to extract user_id
        basic_config = {"configurable": {"thread_id": thread_id}}
        curr_state = self.workflow_instance.get_state(basic_config)
        values = curr_state.values
        user_id = values.get("user_id", "")

        config: RunnableConfig = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "user_id": user_id,
            },
        )
        # Set is_processing to True
        values["is_processing"] = True
        self.workflow_instance.update_state(config=config, values=values)
        self.langfuse_handler = get_langfuse_callback_handler(
            session_id=thread_id,
            user_id=values.get("userId"),
            metadata={"workflow": self.workflow_name},
            tags=["workflow", self.workflow_name],
        )
        config["callbacks"] = [self.langfuse_handler] if self.langfuse_handler else []
        # Update config metadata with userId and workflow name
        if values.get("finished"):
            if values["finished"] is True:
                return {"error": "Chat has already ended"}, "workflow_interrupt", ""
        messages = values.get("messages", [])
        # Remove this line
        # temp_prompt = get_prompt_from_langfuse("GET_CHAT_NAME_PROMPT", words_count="2-6")
        updated_state = {**values}
        if message:
            user_message = BaseMessage(
                content=message.get("content", ""),
                type=message.get("type", ""),
                role=message.get("role", ""),
                file=message.get("file", ""),
            )
            messages.append(user_message)
            updated_state["messages"] = messages
        if file:
            updated_state = {**values, "file": file}
            updated_state["messages"] = messages
        if kwargs:
            for key, value in kwargs["kwargs"].items():
                if key == "image":
                    updated_state["design_variables_image"] = value
                if key == "content":
                    updated_state["design_variables_content"] = value
                if key == "entry":
                    updated_state["entry"] = value
                if key == "enhanced":
                    updated_state["enhanced"] = value
                if key == "theme_id":
                    updated_state["theme_id"] = value
        updated_state["stream"] = False
        self.workflow_instance.update_state(config=config, values=updated_state)
        latest_event = None
        latest_update = None
        for event in self.workflow_instance.stream(
            None, config, stream_mode=["values", "updates"]
        ):
            if event[0] == "updates":
                latest_update = event
            else:
                latest_event = event

        # Set is_processing to False before returning
        if latest_event and latest_event[1]:
            latest_event[1]["is_processing"] = False
            self.workflow_instance.update_state(config=config, values=latest_event[1])

        if latest_update is not None:
            interrupt = latest_update[1].get("__interrupt__")
            if interrupt:
                return latest_event[1], "node_interrupt", interrupt[0].value
        return latest_event[1], "workflow_interrupt", ""

    def get_state(self, thread_id: str) -> dict:
        """Retrieve the current state of the workflow given a thread ID."""
        config = {"configurable": {"thread_id": thread_id}}
        curr_state = self.workflow_instance.get_state(config)
        return curr_state

    def resume_workflow(self, thread_id: str, message: dict) -> dict:
        """Resume interrupted workflow given a thread ID."""
        # First get state with basic config to extract user_id
        basic_config = {"configurable": {"thread_id": thread_id}}
        curr_state = self.workflow_instance.get_state(basic_config)
        values = curr_state.values
        user_id = values.get("user_id", "")

        config: RunnableConfig = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "user_id": user_id,
            },
        )

        # Set is_processing to True
        values["is_processing"] = True
        self.workflow_instance.update_state(config=config, values=values)

        self.langfuse_handler = get_langfuse_callback_handler(
            session_id=thread_id,
            user_id=values.get("userId"),
            metadata={"workflow": self.workflow_name},
            tags=["workflow", self.workflow_name],
        )
        config["callbacks"] = [self.langfuse_handler] if self.langfuse_handler else []
        if values.get("finished"):
            if values["finished"] is True:
                return "Chat has ended"
        if message:
            user_message = BaseMessage(
                content=message.get("content", ""),
                type=message.get("type", ""),
                role=message.get("role", ""),
                file=message.get("file", ""),
            )
            values["messages"].append(user_message)
            for event in self.workflow_instance.stream(
                Command(resume=message.get("content", "")), config, stream_mode="values"
            ):
                latest_event = event

            # Set is_processing to False before returning
            if latest_event[1]:
                latest_event[1]["is_processing"] = False
                self.workflow_instance.update_state(
                    config=config, values=latest_event[1]
                )

            return latest_event
        else:
            for event in self.workflow_instance.stream(
                None, config, stream_mode="values"
            ):
                latest_event = event

            # Set is_processing to False before returning
            if latest_event[1]:
                latest_event[1]["is_processing"] = False
                self.workflow_instance.update_state(
                    config=config, values=latest_event[1]
                )

            return latest_event

    def start_stream(self, message: dict = {}, **kwargs):
        """Start a workflow session, returning a stream of events."""
        thread_id = stripped_uuid4()
        user_id = kwargs["kwargs"].get("userId")
        self.langfuse_handler = get_langfuse_callback_handler(
            session_id=thread_id,
            user_id=user_id,
            metadata={"workflow": self.workflow_name},
            tags=["workflow", self.workflow_name],
        )
        initial_state = deepcopy(self.initial_state)
        initial_state["session_id"] = thread_id
        initial_state["stream"] = True
        initial_state["is_processing"] = True
        if kwargs:
            for key, value in kwargs["kwargs"].items():
                initial_state[key] = value
        if (
            len(initial_state.get("messages", [])) == 0
            and not message
            and self.initial_message
        ):
            initial_state["messages"].append(self.initial_message)
        config: RunnableConfig = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "user_id": user_id,
            },
            callbacks=[self.langfuse_handler] if self.langfuse_handler else [],
        )
        if message:
            initial_message = BaseMessage(
                content=message.get("content", "hello"),
                type=message.get("type", ""),
                role=message.get("role", ""),
                file=message.get("file", ""),
                image=message.get("image", ""),
                index=message.get("index", ""),
            )
            initial_state["messages"].append(initial_message)
            events = []
            for event in self.workflow_instance.stream(
                initial_state, config, stream_mode=["values", "updates", "custom"]
            ):
                events.append(event)
                yield thread_id, event

            # Set is_processing to False after all events
            if (
                events
                and events[-1]
                and events[-1][1]
                and isinstance(events[-1][1], dict)
            ):
                final_state = events[-1][1]
                final_state["is_processing"] = False
                self.workflow_instance.update_state(config=config, values=final_state)
        else:
            self.workflow_instance.update_state(config=config, values=initial_state)
            # Set is_processing to False after initial state update
            initial_state["is_processing"] = False
            self.workflow_instance.update_state(config=config, values=initial_state)
            yield thread_id, initial_state

    def chat_stream(
        self, thread_id: dict, message: dict = {}, file: Optional[str] = None, **kwargs
    ):
        """Start a chat session with a workflow, returning a stream of events."""
        # First get state with basic config to extract user_id
        basic_config = {"configurable": {"thread_id": thread_id}}
        curr_state = self.workflow_instance.get_state(basic_config)
        values = curr_state.values
        user_id = values.get("user_id", "")

        config: RunnableConfig = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "user_id": user_id,
            },
        )

        values["is_processing"] = True
        self.workflow_instance.update_state(config=config, values=values)

        self.langfuse_handler = get_langfuse_callback_handler(
            session_id=thread_id,
            user_id=values.get("userId"),
            metadata={"workflow": self.workflow_name},
            tags=["workflow", self.workflow_name],
        )
        if values.get("finished"):
            if values["finished"] is True:
                return {"error": "Chat has already ended"}, "workflow_interrupt"
        messages = values.get("messages", [])
        self.workflow_instance.update_state(
            config=config, values={**values, "stream": True}
        )
        if message:
            user_message = BaseMessage(
                content=message.get("content", ""),
                type=message.get("type", ""),
                role=message.get("role", ""),
                file=message.get("file", ""),
            )
            messages.append(user_message)
            self.workflow_instance.update_state(
                config=config, values={**values, "messages": messages, "stream": True}
            )
        if file:
            self.workflow_instance.update_state(
                config=config, values={**values, "file": file}
            )

        events = []
        for event in self.workflow_instance.stream(
            None, config, stream_mode=["custom", "values", "updates"]
        ):
            events.append(event)
            yield event

        if events and events[-1] and events[-1][1] and isinstance(events[-1][1], dict):
            final_state = events[-1][1]
            final_state["is_processing"] = False
            self.workflow_instance.update_state(config=config, values=final_state)

    def get_workflow_instance(self):
        return self.workflow_instance
