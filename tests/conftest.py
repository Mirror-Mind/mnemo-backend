"""
Pytest configuration and shared fixtures for orbia-backend tests.
"""

import os
import sys

import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage

from agents.workflows.whatsapp.nodes import WhatsAppNodes
from agents.workflows.whatsapp.tools import WhatsAppTools


@pytest.fixture
def whatsapp_nodes():
    """Fixture to provide WhatsApp nodes instance for testing."""
    return WhatsAppNodes(workflow_name="test_workflow")


@pytest.fixture
def whatsapp_tools():
    """Fixture to provide WhatsApp tools instance for testing."""
    return WhatsAppTools()


@pytest.fixture
def sample_user_state():
    """Fixture to provide a sample user state for testing."""
    return {
        "user_id": "test_user_123",
        "session_id": "test_session_123",
        "user_details": {"name": "Test User", "phone": "+1234567890"},
    }


@pytest.fixture
def sample_message_state(sample_user_state):
    """Fixture to provide a sample message state for testing."""
    return {
        **sample_user_state,
        "messages": [HumanMessage(content="Hello, this is a test message")],
    }


@pytest.fixture
def tool_map(whatsapp_tools):
    """Fixture to provide a mapping of tool names to tool objects."""
    all_tools = whatsapp_tools.get_all_tools()
    return {tool.name: tool for tool in all_tools}


@pytest.fixture
def math_test_cases():
    """Fixture providing test cases for math calculations."""
    return [
        {"expression": "25 * 4 + 10", "expected": 110},
        {"expression": "100 / 5", "expected": 20},
        {"expression": "2 ** 3", "expected": 8},
        {"expression": "15 - 3 * 2", "expected": 9},
    ]


@pytest.fixture
def text_analysis_test_cases():
    """Fixture providing test cases for text analysis."""
    return [
        {
            "text": "Hello world!",
            "expected_words": 2,
            "expected_chars": 12,
            "expected_lines": 1,
        },
        {
            "text": "This is a test\nwith multiple lines",
            "expected_words": 7,
            "expected_chars": 35,
            "expected_lines": 2,
        },
        {"text": "", "expected_words": 0, "expected_chars": 0, "expected_lines": 1},
    ]
