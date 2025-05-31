#!/usr/bin/env python3
"""
Example demonstrating ReAct agent functionality in LangChain wrapper.

The ReAct agent will automatically execute tools and continue the conversation
until it reaches a final answer without tool calls.
"""

from typing import Any, Dict

from agents.utils.langchain_wrapper import LangChainCompletion


class CalculatorTool:
    """Example calculator tool for demonstration."""

    name = "calculator"
    description = "Perform basic arithmetic operations"

    def invoke(self, args: Dict[str, Any]) -> str:
        """Execute calculator operations."""
        operation = args.get("operation")
        a = float(args.get("a", 0))
        b = float(args.get("b", 0))

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return "Error: Division by zero"
            result = a / b
        else:
            return f"Error: Unknown operation '{operation}'"

        return f"The result of {a} {operation} {b} is {result}"


class WebSearchTool:
    """Example web search tool for demonstration."""

    name = "web_search"
    description = "Search the web for information"

    def invoke(self, args: Dict[str, Any]) -> str:
        """Simulate web search."""
        query = args.get("query", "")
        # Simulate search results
        return (
            f"Search results for '{query}': Found relevant information about {query}."
        )


def example_react_agent():
    """Demonstrate ReAct agent with math problem."""

    # Create tools
    calculator = CalculatorTool()
    web_search = WebSearchTool()

    # Conversation messages
    messages = [
        {
            "role": "system",
            "content": """You are a helpful assistant with access to tools. 
            Use the calculator tool to solve math problems step by step.
            Use the web_search tool if you need to look up information.
            Always show your work and explain your reasoning.""",
        },
        {
            "role": "user",
            "content": "I need to calculate the total cost. I bought 3 items at $15.99 each, and there's a 8.5% tax. What's the total?",
        },
    ]

    try:
        print("🤖 Starting ReAct Agent Example")
        print("=" * 50)
        print(f"User: {messages[1]['content']}")
        print("\n🔄 ReAct Agent Processing...")
        print("-" * 30)

        # Call the LangChain completion with ReAct mode
        response = LangChainCompletion(
            model="openai/gpt-3.5-turbo",  # or any supported model
            messages=messages,
            tools=[calculator, web_search],
            tool_choice="react",  # This enables ReAct agent mode
            session_id="example_session",
            userId="example_user",
        )

        print("\n✅ Final Response:")
        print("-" * 20)
        print(response.content)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nNote: Make sure you have the appropriate API keys set up.")


def example_regular_vs_react():
    """Compare regular tool calling vs ReAct agent."""

    calculator = CalculatorTool()

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with a calculator tool.",
        },
        {"role": "user", "content": "What is (5 + 3) * 2?"},
    ]

    print("🔄 Comparison: Regular vs ReAct")
    print("=" * 40)

    try:
        # Regular tool calling (auto)
        print("\n1️⃣ Regular Tool Calling (auto):")
        print("-" * 25)
        response_auto = LangChainCompletion(
            model="openai/gpt-3.5-turbo",
            messages=messages,
            tools=[calculator],
            tool_choice="auto",  # Regular auto mode
            session_id="regular_session",
            userId="example_user",
        )
        print(f"Response: {response_auto.content}")

        # ReAct agent
        print("\n2️⃣ ReAct Agent Mode:")
        print("-" * 18)
        response_react = LangChainCompletion(
            model="openai/gpt-3.5-turbo",
            messages=messages,
            tools=[calculator],
            tool_choice="react",  # ReAct mode - automatic recursion
            session_id="react_session",
            userId="example_user",
        )
        print(f"Response: {response_react.content}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("🚀 ReAct Agent Examples")
    print("=" * 50)

    # Run the main example
    example_react_agent()

    print("\n" + "=" * 50)

    # Run comparison example
    example_regular_vs_react()

    print("\n" + "=" * 50)
    print("📝 Key Differences:")
    print("- Regular mode: Returns tool calls for you to handle")
    print("- ReAct mode: Automatically executes tools and continues until final answer")
    print("- ReAct mode: Perfect for autonomous agents that need to chain tool calls")
