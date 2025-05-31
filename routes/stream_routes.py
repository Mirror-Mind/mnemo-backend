import base64
import inspect
import json
import os
from typing import Union

from fastapi import APIRouter, File, Form, Path, Request, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages.base import messages_to_dict

from agents.utils.tenant_config import get_default_orchestrator
from constants.exceptions import Exceptions

# Create an API router specifically for workflow-related routes
router = APIRouter()


@router.get("/{workflowName}/{threadId}")
async def get_workflow_state(
    request: Request,
    workflowName: str = Path(..., description="Name of the workflow"),
    threadId: str = Path(..., description="Thread ID of the workflow"),
):
    """
    Retrieves the current state of an active workflow.
    """
    try:
        workflow_orchestrator = get_default_orchestrator()
        state = workflow_orchestrator.get_state(workflowName, threadId)
        return {"status": "success", "state": state}
    except Exception as e:
        raise Exceptions.general_exception(
            500, f"Could not fetch workflow state: {str(e)}"
        )


@router.post("/{workflowName}/{threadId}/resume")
async def resume_workflow(
    request: Request,
    workflowName: str = Path(..., description="Name of the workflow"),
    threadId: str = Path(..., description="Thread ID of the workflow"),
):
    """
    Resumes a workflow from a given thread ID.
    """
    try:
        message = await request.json()
    except Exception as e:
        raise Exceptions.json_exception(400, e)

    try:
        workflow_orchestrator = get_default_orchestrator()
        state = workflow_orchestrator.resume_workflow(workflowName, threadId, message)
        return {"status": "success", "state": state}
    except Exception as e:
        raise Exceptions.general_exception(500, f"Could not resume workflow: {str(e)}")


@router.post("/{workflowName}")
async def start_stream_workflow(
    request: Request,
    workflowName: str = Path(..., description="Name of the workflow"),
    file: Union[UploadFile, None] = File(None, description="Optional uploaded file"),
    image: Union[UploadFile, None] = File(None, description="Optional uploaded image"),
    mask_image: Union[UploadFile, None] = File(
        None, description="Optional uploaded mask image for inpainting"
    ),
    message: Union[str, None] = Form(
        None,
        description="Optional message to be sent when caption is needed next to image",
    ),
):
    """
    Initiates a new workflow based on the provided workflow name.
    Returns a unique threadId and the initial state of the workflow.
    """
    try:
        design_system_namespace = request.headers.get(
            "Designsystemnamespace", "default"
        )
        query_params = dict(request.query_params)
        workflow_orchestrator = get_default_orchestrator()
        message_dict = {}

        if request.headers.get("Content-Type") == "application/json":
            message = await request.body()
            try:
                messageJson = json.loads(message)
                message_dict.update(messageJson)
            except Exception as e:
                raise Exceptions.json_exception(400, e)
        else:
            if file:
                file_content = await file.read()
                encoded_file = base64.b64encode(file_content).decode("utf-8")
                message_dict["file"] = encoded_file

            if image:
                image_content = await image.read()
                encoded_image = base64.b64encode(image_content).decode("utf-8")
                # Log image content details to debug file
                logs_dir = "logs/image_gen"
                os.makedirs(logs_dir, exist_ok=True)
                with open(f"{logs_dir}/stream_route_debug.log", "a") as f:
                    f.write("\n--- STREAM IMAGE UPLOAD ---\n")
                    f.write(f"Image filename: {image.filename}\n")
                    f.write(f"Image content type: {image.content_type}\n")
                    f.write(f"Image size: {len(image_content)} bytes\n")
                    f.write(
                        f"Encoded image (first 100 chars): {encoded_image[:100]}...\n"
                    )

                message_dict["image"] = (
                    f"data:{image.content_type};base64,{encoded_image}"
                )
                message_dict["type"] = "image_to_image"
                message_dict["role"] = "user"
                message_dict["content"] = message

            if mask_image:
                mask_content = await mask_image.read()
                encoded_mask = base64.b64encode(mask_content).decode("utf-8")
                # Log mask image content details
                logs_dir = "logs/image_gen"
                os.makedirs(logs_dir, exist_ok=True)
                with open(f"{logs_dir}/stream_route_debug.log", "a") as f:
                    f.write("\n--- STREAM MASK IMAGE UPLOAD ---\n")
                    f.write(f"Mask filename: {mask_image.filename}\n")
                    f.write(f"Mask content type: {mask_image.content_type}\n")
                    f.write(f"Mask size: {len(mask_content)} bytes\n")
                    f.write(
                        f"Encoded mask (first 100 chars): {encoded_mask[:100]}...\n"
                    )

                message_dict["mask"] = (
                    f"data:{mask_image.content_type};base64,{encoded_mask}"
                )
                # If we have both image and mask_image, set type to inpainting
                if image:
                    message_dict["type"] = "inpainting"

        event_generator = workflow_orchestrator.start_stream_workflow(
            workflowName,
            message=message_dict,
            design_system_namespace=design_system_namespace,
            **query_params,
        )

        def stream_events():
            for event in event_generator:
                if inspect.isgenerator(event):
                    for sub_event in event:
                        yield format_event(sub_event)
                else:
                    yield format_event(event)

        return StreamingResponse(stream_events(), media_type="text/event-stream")
    except Exception as e:
        raise Exceptions.general_exception(500, f"Could not start workflow: {str(e)}")


@router.post("/{workflowName}/{threadId}")
async def chat_stream_workflow(
    request: Request,
    workflowName: str = Path(..., description="Name of the workflow"),
    threadId: str = Path(..., description="Thread ID of the workflow"),
    file: Union[UploadFile, None] = File(None, description="Optional uploaded file"),
    image: Union[UploadFile, None] = File(None, description="Optional uploaded image"),
    mask_image: Union[UploadFile, None] = File(
        None, description="Optional uploaded mask image for inpainting"
    ),
    message: Union[str, None] = Form(
        None,
        description="Optional message to be sent when caption is needed next to image",
    ),
):
    """
    Sends additional input to an active workflow.
    Accepts a JSON message and an optional file to continue the workflow session.
    """
    try:
        # Initialize message_dict
        message_dict = {}

        if request.headers.get("Content-Type") == "application/json":
            message_body = await request.body()
            if message_body:
                try:
                    message_dict = json.loads(message_body)
                except json.JSONDecodeError as e:
                    raise Exceptions.json_exception(400, e)

        workflow_orchestrator = get_default_orchestrator()
        if not threadId:
            raise Exceptions.required_and_type_exception("Thread ID")

        # Process form data if present
        if file:
            file_content = await file.read()
            encoded_file = base64.b64encode(file_content).decode("utf-8")
            message_dict["file"] = encoded_file

        if image:
            image_content = await image.read()
            encoded_image = base64.b64encode(image_content).decode("utf-8")
            # Log image content details to debug file
            logs_dir = "logs/image_gen"
            os.makedirs(logs_dir, exist_ok=True)
            with open(f"{logs_dir}/stream_route_debug.log", "a") as f:
                f.write("\n--- STREAM CHAT IMAGE UPLOAD ---\n")
                f.write(f"Image filename: {image.filename}\n")
                f.write(f"Image content type: {image.content_type}\n")
                f.write(f"Image size: {len(image_content)} bytes\n")
                f.write(f"Encoded image (first 100 chars): {encoded_image[:100]}...\n")

            message_dict["image"] = f"data:{image.content_type};base64,{encoded_image}"
            message_dict["type"] = "image_to_image"
            message_dict["role"] = "user"
            message_dict["content"] = message

        if mask_image:
            mask_content = await mask_image.read()
            encoded_mask = base64.b64encode(mask_content).decode("utf-8")
            # Log mask image content details
            logs_dir = "logs/image_gen"
            os.makedirs(logs_dir, exist_ok=True)
            with open(f"{logs_dir}/stream_route_debug.log", "a") as f:
                f.write("\n--- STREAM CHAT MASK IMAGE UPLOAD ---\n")
                f.write(f"Mask filename: {mask_image.filename}\n")
                f.write(f"Mask content type: {mask_image.content_type}\n")
                f.write(f"Mask size: {len(mask_content)} bytes\n")
                f.write(f"Encoded mask (first 100 chars): {encoded_mask[:100]}...\n")

            message_dict["mask"] = (
                f"data:{mask_image.content_type};base64,{encoded_mask}"
            )
            # If we have both image and mask_image, set type to inpainting
            if image:
                message_dict["type"] = "inpainting"

        # Log the final message_dict before sending to workflow
        logs_dir = "logs/image_gen"
        os.makedirs(logs_dir, exist_ok=True)
        with open(f"{logs_dir}/stream_route_debug.log", "a") as f:
            f.write("\n--- FINAL STREAM CHAT MESSAGE DICT ---\n")
            f.write(f"message_dict keys: {message_dict.keys()}\n")
            f.write(f"message_dict type: {message_dict.get('type')}\n")
            if "image" in message_dict:
                img_preview = (
                    message_dict["image"][:100] + "..."
                    if len(message_dict["image"]) > 100
                    else message_dict["image"]
                )
                f.write(f"image data preview: {img_preview}\n")
            if "mask" in message_dict:
                mask_preview = (
                    message_dict["mask"][:100] + "..."
                    if len(message_dict["mask"]) > 100
                    else message_dict["mask"]
                )
                f.write(f"mask data preview: {mask_preview}\n")
            f.write(f"prompt/content: {message_dict.get('content')}\n")

        event_generator = workflow_orchestrator.chat_stream_workflow(
            workflowName, threadId, message_dict
        )

        def stream_events():
            for event in event_generator:
                if inspect.isgenerator(event):
                    for sub_event in event:
                        yield format_event(sub_event)
                else:
                    yield format_event(event)

        return StreamingResponse(stream_events(), media_type="text/event-stream")
    except Exception as e:
        raise Exceptions.general_exception(500, f"Could not continue chat: {str(e)}")


def format_event(event_data) -> bytes:
    """Safely serialize data to JSON SSE format."""
    if isinstance(event_data, tuple) and len(event_data) == 2:
        event_type, payload = event_data
        event_data = {"type": event_type, "payload": payload}
    elif not isinstance(event_data, dict):
        # Convert non-dicts to a safe format
        event_data = {"data": str(event_data)}

    # Wrap 'messages' key with messages_to_list if it exists
    def wrap_messages(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "messages":
                    data[key] = messages_to_dict(value)
                elif isinstance(value, dict):
                    wrap_messages(value)
                elif isinstance(value, list):
                    for item in value:
                        wrap_messages(item)

    def get_interrupt_dict(data):
        if "payload" in data and "__interupt__" in data["payload"]:
            interrupt = data["payload"]["__interupt__"]
            if interrupt:
                return {
                    "type": data["type"],
                    "payload": {
                        "__interupt__": {
                            "values": interrupt.values,
                            "resumable": interrupt.resumable,
                            "ns": interrupt.ns,
                        }
                    },
                }
        return data

    wrap_messages(event_data)
    event_data = get_interrupt_dict(event_data)
    serialized_data = f"data: {json.dumps(event_data)}\n\n".encode()
    return serialized_data
