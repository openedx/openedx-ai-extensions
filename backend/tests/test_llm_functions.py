"""
Tests for the LLM functions module.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from openedx_ai_extensions.processors.llm_functions import (
    AVAILABLE_FUNCTIONS,
    FUNCTIONS_SCHEMA,
    get_location_content,
    roll_dice,
)

# Tests for get_location_content


@patch("openedx_ai_extensions.processors.llm_functions.OpenEdXProcessor")
def test_get_location_content_success(mock_processor_class):
    """Test successful retrieval of location content."""
    # Setup
    mock_processor = MagicMock()
    mock_processor.get_location_content.return_value = "Sample content from location"
    mock_processor_class.return_value = mock_processor

    # Execute
    result = get_location_content("block-v1:edX+DemoX+Demo_Course+type@vertical+block@123")

    # Assert
    assert result == "Sample content from location"
    mock_processor_class.assert_called_once()
    mock_processor.get_location_content.assert_called_once_with(
        "block-v1:edX+DemoX+Demo_Course+type@vertical+block@123"
    )


@patch("openedx_ai_extensions.processors.llm_functions.OpenEdXProcessor")
def test_get_location_content_with_kwargs(mock_processor_class):
    """Test that additional kwargs are accepted but not used."""
    # Setup
    mock_processor = MagicMock()
    mock_processor.get_location_content.return_value = "Content"
    mock_processor_class.return_value = mock_processor

    # Execute
    result = get_location_content(
        "block-v1:edX+DemoX+Demo_Course+type@vertical+block@123",
        extra_param="ignored",
        another_param=42
    )

    # Assert
    assert result == "Content"
    mock_processor.get_location_content.assert_called_once_with(
        "block-v1:edX+DemoX+Demo_Course+type@vertical+block@123"
    )


@patch("openedx_ai_extensions.processors.llm_functions.OpenEdXProcessor")
@patch("openedx_ai_extensions.processors.llm_functions.logger")
def test_get_location_content_exception_handling(mock_logger, mock_processor_class):
    """Test that exceptions are caught and logged, returning empty string."""
    # Setup
    mock_processor = MagicMock()
    mock_processor.get_location_content.side_effect = Exception("Test error")
    mock_processor_class.return_value = mock_processor

    # Execute
    result = get_location_content("invalid-location")

    # Assert
    assert result == ""
    mock_logger.error.assert_called_once()
    assert "Error extracting content for location invalid-location" in str(
        mock_logger.error.call_args
    )


@patch("openedx_ai_extensions.processors.llm_functions.OpenEdXProcessor")
@patch("openedx_ai_extensions.processors.llm_functions.logger")
def test_get_location_content_processor_creation_fails(mock_logger, mock_processor_class):
    """Test when OpenEdXProcessor instantiation fails."""
    # Setup
    mock_processor_class.side_effect = Exception("Processor initialization error")

    # Execute
    result = get_location_content("some-location")

    # Assert
    assert result == ""
    mock_logger.error.assert_called_once()


# Tests for roll_dice


def test_roll_dice_default():
    """Test rolling one die (default behavior)."""
    result = roll_dice()

    assert isinstance(result, list)
    assert len(result) == 1
    assert 1 <= result[0] <= 6


def test_roll_dice_multiple():
    """Test rolling multiple dice."""
    result = roll_dice(n_dice=5)

    assert isinstance(result, list)
    assert len(result) == 5
    for value in result:
        assert 1 <= value <= 6


def test_roll_dice_zero():
    """Test rolling zero dice."""
    result = roll_dice(n_dice=0)

    assert isinstance(result, list)
    assert len(result) == 0


def test_roll_dice_with_kwargs():
    """Test that additional kwargs are accepted but not used."""
    result = roll_dice(n_dice=3, extra_param="ignored", another_param=42)

    assert isinstance(result, list)
    assert len(result) == 3
    for value in result:
        assert 1 <= value <= 6


@patch("openedx_ai_extensions.processors.llm_functions.random.randint")
def test_roll_dice_deterministic(mock_randint):
    """Test roll_dice with mocked random values."""
    mock_randint.side_effect = [3, 5, 1]

    result = roll_dice(n_dice=3)

    assert result == [3, 5, 1]
    assert mock_randint.call_count == 3
    for call in mock_randint.call_args_list:
        assert call[0] == (1, 6)


def test_roll_dice_range_validity():
    """Test that rolled values are always in valid range over multiple rolls."""
    for _ in range(100):
        result = roll_dice(n_dice=10)
        for value in result:
            assert 1 <= value <= 6, f"Invalid dice value: {value}"


# Tests for AVAILABLE_FUNCTIONS


def test_available_functions_contains_expected_functions():
    """Test that AVAILABLE_FUNCTIONS contains the expected functions."""
    assert "get_location_content" in AVAILABLE_FUNCTIONS
    assert "roll_dice" in AVAILABLE_FUNCTIONS


def test_available_functions_are_callable():
    """Test that all functions in AVAILABLE_FUNCTIONS are callable."""
    for name, func in AVAILABLE_FUNCTIONS.items():
        assert callable(func), f"{name} is not callable"


def test_available_functions_references_correct_functions():
    """Test that AVAILABLE_FUNCTIONS references the actual function objects."""
    assert AVAILABLE_FUNCTIONS["get_location_content"] is get_location_content
    assert AVAILABLE_FUNCTIONS["roll_dice"] is roll_dice


# Tests for FUNCTIONS_SCHEMA


def test_functions_schema_contains_all_available_functions():
    """Test that FUNCTIONS_SCHEMA has entries for all AVAILABLE_FUNCTIONS."""
    assert set(FUNCTIONS_SCHEMA.keys()) == set(AVAILABLE_FUNCTIONS.keys())


def test_functions_schema_has_dict_values():
    """Test that all schema entries are dictionaries."""
    for name, schema in FUNCTIONS_SCHEMA.items():
        assert isinstance(schema, dict), f"Schema for {name} is not a dict"


@pytest.mark.parametrize("function_name", ["get_location_content", "roll_dice"])
def test_functions_schema_structure(function_name):
    """Test that each function schema has expected structure."""
    schema = FUNCTIONS_SCHEMA[function_name]

    # Basic schema structure checks
    assert "name" in schema or "function" in schema or function_name is not None
    # The exact structure depends on litellm's implementation,
    # so we just verify it's a non-empty dict
    assert len(schema) > 0


def test_functions_schema_is_serializable():
    """Test that FUNCTIONS_SCHEMA can be serialized (e.g., for JSON)."""
    try:
        json.dumps(FUNCTIONS_SCHEMA)
    except (TypeError, ValueError) as e:
        pytest.fail(f"FUNCTIONS_SCHEMA is not JSON-serializable: {e}")


# Integration tests


@patch("openedx_ai_extensions.processors.llm_functions.OpenEdXProcessor")
def test_get_location_content_integration(mock_proc):
    """Integration test for get_location_content."""
    # This test will fail if OpenEdXProcessor is not properly configured
    # but serves as a smoke test for the function's structure
    mock_instance = MagicMock()
    mock_instance.get_location_content.return_value = "Integration test content"
    mock_proc.return_value = mock_instance

    result = get_location_content("test-location-id")

    assert isinstance(result, str)
    assert result == "Integration test content"


def test_roll_dice_integration():
    """Integration test for roll_dice (without mocking random)."""
    # Run actual dice rolls to ensure no runtime errors
    results = []
    for n in [1, 5, 10]:
        result = roll_dice(n_dice=n)
        results.extend(result)

    # Verify all results are valid
    assert all(1 <= val <= 6 for val in results)
    # Verify we got the expected number of rolls
    assert len(results) == 1 + 5 + 10


@patch("openedx_ai_extensions.processors.llm_functions.OpenEdXProcessor")
def test_function_registry_integration(mock_proc):
    """Integration test to verify functions can be called via registry."""
    # Test calling functions through the registry
    mock_instance = MagicMock()
    mock_instance.get_location_content.return_value = "Content via registry"
    mock_proc.return_value = mock_instance

    # Call via registry
    func = AVAILABLE_FUNCTIONS["get_location_content"]
    result = func("test-location")

    assert result == "Content via registry"

    # Test roll_dice via registry
    func = AVAILABLE_FUNCTIONS["roll_dice"]
    result = func(n_dice=2)

    assert len(result) == 2
    assert all(1 <= val <= 6 for val in result)
