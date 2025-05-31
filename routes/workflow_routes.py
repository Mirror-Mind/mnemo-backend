import base64
import json
import traceback
from typing import Union

import requests
from fastapi import APIRouter, File, Form, HTTPException, Path, Request, UploadFile
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect

from agents.utils.tenant_config import get_default_orchestrator
from constants.exceptions import Exceptions
from helpers.logger_config import logger

# Create an API router specifically for workflow-related routes
router = APIRouter()


@router.post("/{workflowName}")
async def start_workflow(
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
    logger.info(f"Starting workflow {workflowName}")
    try:
        query_params = dict(request.query_params)
        if hasattr(request.state, "user_id") and request.state.user_id:
            query_params["userId"] = request.state.user_id
        workflow_orchestrator = get_default_orchestrator()
        message_dict = {}
        try:
            if request.headers.get("Content-Type") == "application/json":
                message = await request.body()
                try:
                    messageJson = json.loads(message)
                    if "type" in messageJson and messageJson["type"] == "image":
                        image_url = messageJson["image_url"]
                        response = requests.get(image_url)
                        image_content = response.content
                        content_type = response.headers.get("Content-Type")
                        if not content_type:
                            if image_url.lower().endswith(
                                ".jpg"
                            ) or image_url.lower().endswith(".jpeg"):
                                content_type = "image/jpeg"
                            elif image_url.lower().endswith(".png"):
                                content_type = "image/png"
                            elif image_url.lower().endswith(".gif"):
                                content_type = "image/gif"
                            elif image_url.lower().endswith(".webp"):
                                content_type = "image/webp"
                            else:
                                content_type = "image/jpeg"
                        encoded_image = base64.b64encode(image_content).decode("utf8")
                        message_dict["image"] = (
                            f"data:{content_type};base64,{encoded_image}"
                        )
                        message_dict["type"] = "image"
                        message_dict["role"] = "user"
                        message_dict["content"] = messageJson["content"]
                    else:
                        message_dict.update(messageJson)
                except json.JSONDecodeError:
                    raise Exceptions.json_exception(400, "Invalid JSON in message")
            elif request.headers.get("Content-Type", "").startswith(
                "multipart/form-data"
            ):
                messageJson = json.loads(message)
                if file:
                    file_content = await file.read()
                    encoded_file = base64.b64encode(file_content).decode("utf8")
                    message_dict["file"] = encoded_file
                    message_dict["type"] = "file"
                    message_dict["role"] = "user"
                    message_dict["content"] = messageJson["content"]

                if image:
                    image_content = await image.read()
                    encoded_image = base64.b64encode(image_content).decode("utf8")
                    message_dict["image"] = (
                        f"data:{image.content_type};base64,{encoded_image}"
                    )
                    message_dict["type"] = "image"
                    message_dict["role"] = "user"
                    message_dict["content"] = message

                if mask_image:
                    mask_content = await mask_image.read()
                    encoded_mask = base64.b64encode(mask_content).decode("utf8")
                    message_dict["mask"] = (
                        f"data:{mask_image.content_type};base64,{encoded_mask}"
                    )
                    # If we have both image and mask_image, set type to inpainting
                    if image:
                        message_dict["type"] = "inpainting"

        except ClientDisconnect:
            # Return a specific response for client disconnection
            return JSONResponse(
                status_code=499,  # Client Closed Request
                content={
                    "status": "error",
                    "message": "Client disconnected while uploading data",
                    "canRetry": True,
                },
            )

        threadId, eventData, type, interrupt_message = workflow_orchestrator.start(
            workflowName,
            message=message_dict,
            **query_params,
        )

        if type == "node_interrupt":
            return {
                "status": "success",
                "type": type,
                "state": eventData,
                "interrupt_message": interrupt_message,
                "threadId": threadId,
            }
        return {
            "status": "success",
            "type": type,
            "state": eventData,
            "threadId": threadId,
        }
    except HTTPException as e:
        raise
    except Exception as e:
        print(traceback.format_exc())
        logger.error(traceback.format_exc())
        raise Exceptions.general_exception(500, str(e))


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
    except HTTPException as e:
        print(traceback.format_exc())
        raise


@router.post("/{workflowName}/{threadId}")
async def chat_workflow(
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
            raise Exceptions.required_and_type_exception("threadId", "string")

        query_params = dict(request.query_params)

        # Process form data if present
        if file:
            file_data = await file.read()
            # Encode the file data to base64
            encoded_file = base64.b64encode(file_data).decode("utf-8")
            message_dict["file"] = encoded_file

        if image:
            image_content = await image.read()
            encoded_image = base64.b64encode(image_content).decode("utf8")
            message_dict["image"] = f"data:{image.content_type};base64,{encoded_image}"
            message_dict["type"] = "image"
            message_dict["role"] = "user"
            message_dict["content"] = message

        if mask_image:
            mask_content = await mask_image.read()
            encoded_mask = base64.b64encode(mask_content).decode("utf8")
            message_dict["mask"] = (
                f"data:{mask_image.content_type};base64,{encoded_mask}"
            )
            if image:
                message_dict["type"] = "inpainting"
        eventData, type, interrupt_message = workflow_orchestrator.chat(
            workflowName, threadId, message_dict, **query_params
        )
        if type == "node_interrupt":
            return {
                "status": "success",
                "type": type,
                "state": eventData,
                "interrupt_message": interrupt_message,
            }
        return {"status": "success", "type": type, "state": eventData}

    except Exception as e:
        print(traceback.format_exc())
        logger.error(traceback.format_exc())
        raise Exceptions.general_exception(500, str(e))


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
    except json.JSONDecodeError:
        message = None
    try:
        workflow_orchestrator = get_default_orchestrator()
        state = workflow_orchestrator.resume_workflow(workflowName, threadId, message)
        return {"status": "success", "state": state}
    except Exception as e:
        print(traceback.format_exc())
        logger.error(traceback.format_exc())
        raise Exceptions.general_exception(500, str(e))
