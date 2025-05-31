"""
Test suite for WhatsApp sample tools using pytest.
"""

import re

import pytest


class TestSampleTools:
    """Test class for sample tools functionality."""

    def test_tools_initialization(self, whatsapp_tools):
        """Test that tools are properly initialized."""
        assert whatsapp_tools is not None
        all_tools = whatsapp_tools.get_all_tools()
        assert len(all_tools) > 0

        # Check that sample tools are included
        tool_names = [tool.name for tool in all_tools]
        expected_sample_tools = [
            "get_current_time",
            "calculate_math",
            "generate_random_number",
            "word_count",
            "reverse_text",
        ]

        for tool_name in expected_sample_tools:
            assert tool_name in tool_names, f"Sample tool '{tool_name}' not found"

    def test_get_current_time_tool(self, tool_map):
        """Test the get_current_time tool."""
        assert "get_current_time" in tool_map

        result = tool_map["get_current_time"].invoke({})

        assert isinstance(result, str)
        assert "UTC" in result
        assert "Current UTC time:" in result

        # Check that the result contains a valid timestamp format
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC"
        assert re.search(timestamp_pattern, result), "Invalid timestamp format"

    @pytest.mark.parametrize(
        "expression,expected",
        [
            ("25 * 4 + 10", 110),
            ("100 / 5", 20),
            ("2 ** 3", 8),
            ("15 - 3 * 2", 9),
            ("(10 + 5) * 2", 30),
        ],
    )
    def test_calculate_math_tool_valid_expressions(
        self, tool_map, expression, expected
    ):
        """Test the calculate_math tool with valid expressions."""
        assert "calculate_math" in tool_map

        result = tool_map["calculate_math"].invoke({"expression": expression})

        assert isinstance(result, str)
        assert "Result:" in result
        assert str(expected) in result
        assert expression in result

    def test_calculate_math_tool_invalid_expressions(self, tool_map):
        """Test the calculate_math tool with invalid expressions."""
        assert "calculate_math" in tool_map

        invalid_expressions = [
            "import os",  # Contains invalid characters
            "exec('print(1)')",  # Contains invalid characters
            "1/0",  # Division by zero
            "invalid_expression",  # Invalid syntax
        ]

        for expression in invalid_expressions:
            result = tool_map["calculate_math"].invoke({"expression": expression})
            assert isinstance(result, str)
            assert "Error" in result

    def test_generate_random_number_tool(self, tool_map):
        """Test the generate_random_number tool."""
        assert "generate_random_number" in tool_map

        # Test with default parameters
        result = tool_map["generate_random_number"].invoke({})
        assert isinstance(result, str)
        assert "Random number between 1 and 100:" in result

        # Extract the number from the result
        number_match = re.search(r"Random number between \d+ and \d+: (\d+)", result)
        assert number_match, "Could not extract random number from result"

        random_num = int(number_match.group(1))
        assert 1 <= random_num <= 100, "Random number not in expected range"

    def test_generate_random_number_tool_custom_range(self, tool_map):
        """Test the generate_random_number tool with custom range."""
        assert "generate_random_number" in tool_map

        result = tool_map["generate_random_number"].invoke(
            {"min_value": 50, "max_value": 60}
        )

        assert isinstance(result, str)
        assert "Random number between 50 and 60:" in result

        # Extract the number from the result
        number_match = re.search(r"Random number between \d+ and \d+: (\d+)", result)
        assert number_match, "Could not extract random number from result"

        random_num = int(number_match.group(1))
        assert 50 <= random_num <= 60, "Random number not in expected range"

    def test_generate_random_number_tool_invalid_range(self, tool_map):
        """Test the generate_random_number tool with invalid range."""
        assert "generate_random_number" in tool_map

        result = tool_map["generate_random_number"].invoke(
            {"min_value": 100, "max_value": 50}
        )

        assert isinstance(result, str)
        assert "Error" in result
        assert "min_value cannot be greater than max_value" in result

    @pytest.mark.parametrize(
        "text,expected_words,expected_chars,expected_lines",
        [
            ("Hello world!", 2, 12, 1),
            ("This is a test\nwith multiple lines", 7, 34, 2),
            ("", 0, 0, 1),
            ("Single", 1, 6, 1),
            ("Line 1\nLine 2\nLine 3", 6, 20, 3),
        ],
    )
    def test_word_count_tool(
        self, tool_map, text, expected_words, expected_chars, expected_lines
    ):
        """Test the word_count tool with various text inputs."""
        assert "word_count" in tool_map

        result = tool_map["word_count"].invoke({"text": text})

        assert isinstance(result, str)
        assert "Text analysis:" in result
        assert f"Words: {expected_words}" in result
        assert f"Characters (with spaces): {expected_chars}" in result
        assert f"Lines: {expected_lines}" in result

    @pytest.mark.parametrize(
        "text,expected_reversed",
        [
            ("Hello", "olleH"),
            ("Hello World", "dlroW olleH"),
            ("12345", "54321"),
            ("", ""),
            ("A", "A"),
            ("Racecar", "racecaR"),
        ],
    )
    def test_reverse_text_tool(self, tool_map, text, expected_reversed):
        """Test the reverse_text tool with various text inputs."""
        assert "reverse_text" in tool_map

        result = tool_map["reverse_text"].invoke({"text": text})

        assert isinstance(result, str)
        assert f"Original: {text}" in result
        assert f"Reversed: {expected_reversed}" in result

    def test_all_sample_tools_have_descriptions(self, whatsapp_tools):
        """Test that all sample tools have proper descriptions."""
        all_tools = whatsapp_tools.get_all_tools()
        sample_tool_names = [
            "get_current_time",
            "calculate_math",
            "generate_random_number",
            "word_count",
            "reverse_text",
        ]

        for tool in all_tools:
            if tool.name in sample_tool_names:
                assert hasattr(tool, "description"), (
                    f"Tool {tool.name} missing description"
                )
                assert tool.description, f"Tool {tool.name} has empty description"
                assert len(tool.description) > 10, (
                    f"Tool {tool.name} description too short"
                )

    def test_tools_are_callable(self, tool_map):
        """Test that all sample tools are callable."""
        sample_tool_names = [
            "get_current_time",
            "calculate_math",
            "generate_random_number",
            "word_count",
            "reverse_text",
        ]

        for tool_name in sample_tool_names:
            assert tool_name in tool_map, f"Tool {tool_name} not found"
            tool = tool_map[tool_name]
            assert hasattr(tool, "invoke"), f"Tool {tool_name} is not callable"
            assert callable(tool.invoke), f"Tool {tool_name}.invoke is not callable"
