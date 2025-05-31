# Test Suite for Orbia Backend

This directory contains the comprehensive test suite for the orbia-backend project, specifically focusing on the LangChain wrapper implementation and WhatsApp workflow functionality.

## Test Structure

### Test Files

- **`test_sample_tools.py`** - Tests for the sample tools (time, math, random number, text analysis)
- **`test_memory_tools.py`** - Tests for memory management tools (search, add, get, delete, update)
- **`test_whatsapp_workflow.py`** - Tests for WhatsApp workflow nodes and integration
- **`test_langchain_wrapper.py`** - Tests for the LangChain wrapper functionality

### Configuration Files

- **`conftest.py`** - Pytest fixtures and shared test configuration
- **`pytest.ini`** - Pytest configuration and settings
- **`README.md`** - This documentation file

## Running Tests

### Prerequisites

Make sure you have the required dependencies installed:

```bash
pip install pytest pytest-mock
```

### Basic Test Execution

Run all tests:
```bash
pytest
```

Run tests with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_sample_tools.py
```

Run specific test class:
```bash
pytest tests/test_sample_tools.py::TestSampleTools
```

Run specific test method:
```bash
pytest tests/test_sample_tools.py::TestSampleTools::test_get_current_time_tool
```

### Test Categories

Run only unit tests:
```bash
pytest -m unit
```

Run only integration tests:
```bash
pytest -m integration
```

Skip slow tests:
```bash
pytest -m "not slow"
```

### Test Coverage

Run tests with coverage report:
```bash
pytest --cov=agents --cov-report=html
```

## Test Categories and Markers

- **`@pytest.mark.unit`** - Unit tests that test individual components in isolation
- **`@pytest.mark.integration`** - Integration tests that test component interactions
- **`@pytest.mark.slow`** - Tests that take longer to run (e.g., API calls)
- **`@pytest.mark.memory`** - Tests that require memory/database setup
- **`@pytest.mark.api`** - Tests that make external API calls

## Test Coverage

### Sample Tools (`test_sample_tools.py`)
- ✅ Tool initialization and discovery
- ✅ Current time tool functionality
- ✅ Math calculation tool with valid/invalid expressions
- ✅ Random number generation with custom ranges
- ✅ Text analysis (word count, character count, line count)
- ✅ Text reversal functionality
- ✅ Tool descriptions and metadata
- ✅ Tool callability verification

### Memory Tools (`test_memory_tools.py`)
- ✅ Memory tool initialization
- ✅ Add memory functionality with/without metadata
- ✅ Search memories with results/no results
- ✅ Get all memories functionality
- ✅ Delete memory with invalid IDs
- ✅ Update memory with invalid IDs
- ✅ Error handling for invalid parameters
- ✅ Tool descriptions verification

### WhatsApp Workflow (`test_whatsapp_workflow.py`)
- ✅ Node initialization
- ✅ Message processing with valid/invalid inputs
- ✅ Response generation
- ✅ WhatsApp response formatting (text, interactive, buttons)
- ✅ Button title truncation
- ✅ Fallback response handling
- ✅ Error recovery mechanisms
- ✅ State preservation across workflow steps
- ✅ Memory integration testing
- ✅ Tool triggering with various message types

### LangChain Wrapper (`test_langchain_wrapper.py`)
- ✅ Wrapper initialization
- ✅ Message cleaning and validation
- ✅ LangChain message conversion
- ✅ Tool format conversion
- ✅ Model string parsing
- ✅ Provider support verification
- ✅ Model caching functionality
- ✅ Error handling for invalid inputs
- ✅ JSON response handling
- ✅ Streaming response handling
- ✅ Tool response handling
- ✅ API key validation

## Fixtures

### Shared Fixtures (from `conftest.py`)

- **`whatsapp_nodes`** - Provides WhatsApp nodes instance
- **`whatsapp_tools`** - Provides WhatsApp tools instance
- **`sample_user_state`** - Sample user state for testing
- **`sample_message_state`** - Sample message state for testing
- **`tool_map`** - Mapping of tool names to tool objects
- **`math_test_cases`** - Test cases for math calculations
- **`text_analysis_test_cases`** - Test cases for text analysis

## Parametrized Tests

Many tests use `@pytest.mark.parametrize` to test multiple scenarios:

- Math expressions with expected results
- Text inputs with expected analysis results
- Model string formats with expected parsing
- Message types that should trigger tools
- Various error conditions

## Mocking and Isolation

Tests use `unittest.mock` to:
- Mock external API calls
- Isolate components for unit testing
- Test error conditions safely
- Verify method calls and interactions

## Best Practices

1. **Isolation** - Each test is independent and doesn't rely on others
2. **Descriptive Names** - Test names clearly describe what is being tested
3. **Arrange-Act-Assert** - Tests follow the AAA pattern
4. **Edge Cases** - Tests cover both happy path and error conditions
5. **Fixtures** - Shared setup is handled through pytest fixtures
6. **Parametrization** - Multiple scenarios are tested efficiently

## Adding New Tests

When adding new tests:

1. Place them in the appropriate test file based on functionality
2. Use descriptive test names that explain the scenario
3. Add appropriate markers (`@pytest.mark.unit`, etc.)
4. Use existing fixtures when possible
5. Follow the established patterns for assertions
6. Test both success and failure cases

## Continuous Integration

These tests are designed to run in CI/CD pipelines and provide:
- Fast feedback on code changes
- Regression detection
- Quality assurance for releases
- Documentation of expected behavior

## Troubleshooting

### Common Issues

1. **Import Errors** - Ensure the project root is in Python path
2. **Missing Dependencies** - Install required packages with pip
3. **API Key Errors** - Some tests mock API calls to avoid requiring real keys
4. **Database Errors** - Memory tests may require database setup

### Debug Mode

Run tests with debugging:
```bash
pytest --pdb
```

Run with print statements visible:
```bash
pytest -s
``` 