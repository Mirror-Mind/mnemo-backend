#!/usr/bin/env python3
"""
Debug script for testing WhatsApp workflow processing.
Run this script to test the WhatsApp workflow with debug logging enabled.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set debug logging environment variables
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["CONCISE_LOGGING"] = "true"

from langchain_core.messages import HumanMessage

from agents.constants.workflow_names import WHATSAPP_WORKFLOW
from agents.utils.tenant_config import get_default_orchestrator
from helpers.logger_config import logger


async def test_whatsapp_workflow():
    """Test the WhatsApp workflow with debug logging."""
    try:
        logger.info("Starting WhatsApp workflow debug test")

        # Test message
        test_message = "Hello, this is a test message"
        test_user_id = "test_user_123"
        test_phone_number = "+1234567890"

        logger.debug(
            "Test parameters",
            data={
                "message": test_message,
                "user_id": test_user_id,
                "phone_number": test_phone_number,
            },
        )

        # Initialize workflow
        logger.debug("Initializing workflow orchestrator")
        workflow_orchestrator = get_default_orchestrator()
        workflow_instance = workflow_orchestrator.get_workflow_instance(
            WHATSAPP_WORKFLOW
        )
        logger.debug("Workflow instance retrieved successfully")

        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=test_message)],
            "user_id": test_user_id,
            "phone_number": test_phone_number,
            "whatsapp_message_id": f"test_msg_{datetime.now().timestamp()}",
            "user_details": {
                "name": "Test User",
                "wa_id": test_user_id,
                "phone_number_id": "test_phone_id",
            },
            "memory_context": None,
            "response_type": "text",
            "response_content": {},
            "stepper": {},
            "finished": False,
            "session_id": f"test_session_{test_user_id}",
            "stream": False,
            "is_processing": True,
            "error": None,
        }

        # Create config
        config = {
            "configurable": {
                "thread_id": initial_state["session_id"],
                "user_id": test_user_id,
            }
        }

        logger.debug(
            "Invoking workflow",
            data={
                "session_id": initial_state["session_id"],
                "user_id": test_user_id,
                "message": test_message,
            },
        )

        # Invoke workflow
        result = workflow_instance.invoke(initial_state, config)

        logger.debug(
            "Workflow result",
            data={
                "result_keys": list(result.keys()) if result else None,
                "finished": result.get("finished") if result else None,
                "has_error": bool(result.get("error")) if result else None,
                "response_content": result.get("response_content") if result else None,
                "error": result.get("error") if result else None,
            },
        )

        if result and result.get("response_content") and not result.get("error"):
            logger.info("✅ Workflow completed successfully!")

            # Get the workflow class to access the nodes
            workflow_class = workflow_orchestrator.agents[WHATSAPP_WORKFLOW]

            # Format response for WhatsApp
            whatsapp_response = workflow_class.whatsapp_nodes.format_whatsapp_response(
                result["response_content"]
            )
            whatsapp_response["to"] = test_phone_number

            logger.info("WhatsApp response formatted", data=whatsapp_response)

        else:
            error_msg = result.get("error") if result else "No response generated"
            logger.error(f"❌ Workflow failed: {error_msg}")

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {str(e)}")
        logger.debug(
            "Exception details",
            data={
                "exception_type": type(e).__name__,
                "exception_args": str(e.args) if hasattr(e, "args") else None,
            },
        )
        import traceback

        logger.debug("Full traceback", data={"traceback": traceback.format_exc()})


if __name__ == "__main__":
    print("🚀 Starting WhatsApp workflow debug test...")
    print("📝 Log level set to DEBUG")
    print("=" * 50)

    asyncio.run(test_whatsapp_workflow())

    print("=" * 50)
    print("✅ Debug test completed. Check logs above for details.")
