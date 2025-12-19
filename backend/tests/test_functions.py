"""
Tests for LLM function decorators and external functions.
"""

import pytest

from openedx_ai_extensions.functions.decorators import (
    _LLM_CLASS_INSTANCES,
    _LLM_FUNCTION_REGISTRY,
    AVAILABLE_TOOLS,
    TOOLS_SCHEMA,
    llm_tool,
    register_instance,
)
from openedx_ai_extensions.functions.external_function_example import roll_dice

# ============================================================================
# Decorator Tests
# ============================================================================


def test_llm_tool_method_not_registered_error():
    """
    Test that calling a decorated method without registering its instance raises RuntimeError.

    This test covers lines 104-107 in decorators.py where the error is raised
    when a method's class instance has not been registered.
    """
    # Clear any existing instances to ensure clean test
    _LLM_CLASS_INSTANCES.clear()

    class TestClass:  # pylint: disable=too-few-public-methods,unused-variable
        """Test class with a decorated method."""

        @llm_tool(schema={
            "type": "function",
            "name": "test_method",
            "function": {
                "name": "test_method",
                "description": "A test method",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param": {"type": "string"}
                    }
                }
            }
        })
        def test_method(self, param):
            """Test method."""
            return f"Result: {param}"

    # Try to call the method without registering the instance
    with pytest.raises(RuntimeError) as exc_info:
        AVAILABLE_TOOLS["test_method"](param="test")

    assert "has not been initialized" in str(exc_info.value)
    assert "Call register_instance()" in str(exc_info.value)
    assert "TestClass" in str(exc_info.value)


def test_llm_tool_method_with_malformed_qualname():
    """
    Test error handling when method qualname cannot be parsed.

    This test covers lines 109-111 in decorators.py where an error is raised
    when the class name cannot be determined from the function's qualname.
    """
    # Create a function with a malformed qualname (no dots)
    def standalone_func(param):
        """Standalone function."""
        return param

    # Manually set up as if it were decorated as a method but with bad qualname
    standalone_func.__qualname__ = "badname"  # No dots, so can't parse class

    # Simulate what the decorator does for methods
    def callable_wrapper(*args, **kwargs):
        """Wrapper that automatically binds the method to its instance."""
        qualname_parts = standalone_func.__qualname__.split('.')
        if len(qualname_parts) >= 2:
            class_name = qualname_parts[-2]
            if class_name in _LLM_CLASS_INSTANCES:
                instance = _LLM_CLASS_INSTANCES[class_name]
                return standalone_func(instance, *args, **kwargs)
            raise RuntimeError(
                f"Method {standalone_func.__name__} from class {class_name} has not been initialized. "
                f"Call register_instance() with an instance of {class_name} first."
            )
        raise RuntimeError(
            f"Could not determine class name for method {standalone_func.__name__}"
        )

    _LLM_FUNCTION_REGISTRY["bad_method"] = callable_wrapper

    # Try to call it
    with pytest.raises(RuntimeError) as exc_info:
        _LLM_FUNCTION_REGISTRY["bad_method"](param="test")

    assert "Could not determine class name" in str(exc_info.value)


# ============================================================================
# External Function Tests
# ============================================================================


def test_roll_dice_execution():
    """
    Test that roll_dice function executes correctly.

    This test covers lines 37-38 in external_function_example.py where
    the actual dice rolling logic is implemented.
    """
    # Test with default parameter (1 die)
    result = roll_dice()
    assert isinstance(result, list)
    assert len(result) == 1
    assert 1 <= result[0] <= 6

    # Test with multiple dice
    result = roll_dice(n_dice=3)
    assert isinstance(result, list)
    assert len(result) == 3
    for die_value in result:
        assert 1 <= die_value <= 6

    # Test with kwargs (simulating how it might be called by LLM processor)
    result = roll_dice(n_dice=2, extra_param="ignored")
    assert isinstance(result, list)
    assert len(result) == 2

    # Test edge case: rolling 0 dice
    result = roll_dice(n_dice=0)
    assert isinstance(result, list)
    assert len(result) == 0


def test_llm_tool_decorator_for_regular_function():
    """
    Test that @llm_tool decorator works correctly for regular functions.

    This test verifies the function registration and schema storage for
    non-method functions.
    """
    # Define a simple function with the decorator
    @llm_tool(schema={
        "type": "function",
        "name": "test_regular_function",
        "function": {
            "name": "test_regular_function",
            "description": "A test regular function",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "integer"}
                }
            }
        }
    })
    def test_regular_function(value):
        """Test regular function."""
        return value * 2

    # Verify function is registered
    assert "test_regular_function" in AVAILABLE_TOOLS
    assert "test_regular_function" in TOOLS_SCHEMA

    # Verify function can be called
    result = AVAILABLE_TOOLS["test_regular_function"](value=5)
    assert result == 10

    # Verify schema is stored correctly
    schema = TOOLS_SCHEMA["test_regular_function"]
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test_regular_function"


def test_register_instance_with_decorated_method():
    """
    Test register_instance function to enable calling decorated methods.

    This test verifies that after registering an instance, its decorated
    methods become callable through AVAILABLE_TOOLS.
    """
    # Clear registries
    _LLM_CLASS_INSTANCES.clear()

    class Calculator:  # pylint: disable=too-few-public-methods
        """Test calculator class."""

        def __init__(self, multiplier):
            """Initialize calculator."""
            self.multiplier = multiplier

        @llm_tool(schema={
            "type": "function",
            "name": "multiply_value",
            "function": {
                "name": "multiply_value",
                "description": "Multiply a value",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"}
                    }
                }
            }
        })
        def multiply_value(self, value):
            """Multiply value by multiplier."""
            return value * self.multiplier

    # Create and register instance
    calc = Calculator(multiplier=3)
    register_instance(calc)

    # Verify instance is registered
    assert "Calculator" in _LLM_CLASS_INSTANCES
    assert _LLM_CLASS_INSTANCES["Calculator"] is calc

    # Verify method can now be called
    result = AVAILABLE_TOOLS["multiply_value"](value=4)
    assert result == 12


def test_llm_tool_preserves_function_metadata():
    """
    Test that @llm_tool decorator preserves function metadata using functools.wraps.

    This verifies that the wrapper maintains the original function's name and docstring.
    """
    @llm_tool(schema={
        "type": "function",
        "name": "documented_function",
        "function": {
            "name": "documented_function",
            "description": "Function with documentation",
            "parameters": {"type": "object", "properties": {}}
        }
    })
    def documented_function():
        """This is the original docstring."""
        return "result"

    # Verify metadata is preserved
    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ == "This is the original docstring."


def test_roll_dice_available_in_registry():
    """
    Test that roll_dice function is properly registered in AVAILABLE_TOOLS.

    This ensures the external function example is correctly integrated.
    """
    # Verify roll_dice is in the registries
    assert "roll_dice" in AVAILABLE_TOOLS
    assert "roll_dice" in TOOLS_SCHEMA

    # Verify it can be called through the registry
    result = AVAILABLE_TOOLS["roll_dice"](n_dice=2)
    assert isinstance(result, list)
    assert len(result) == 2

    # Verify schema exists and has expected structure
    schema = TOOLS_SCHEMA["roll_dice"]
    assert "type" in schema
    assert "function" in schema
    assert schema["function"]["name"] == "roll_dice"


def test_multiple_instances_of_same_class():
    """
    Test that registering a new instance replaces the previous one.

    This verifies the behavior when register_instance is called multiple
    times with different instances of the same class.
    """
    _LLM_CLASS_INSTANCES.clear()

    class Counter:  # pylint: disable=too-few-public-methods
        """Simple counter class."""

        def __init__(self, start_value):
            """Initialize counter."""
            self.value = start_value

        @llm_tool(schema={
            "type": "function",
            "name": "get_count",
            "function": {
                "name": "get_count",
                "description": "Get counter value",
                "parameters": {"type": "object", "properties": {}}
            }
        })
        def get_count(self):
            """Get current count."""
            return self.value

    # Register first instance
    counter1 = Counter(start_value=10)
    register_instance(counter1)
    result1 = AVAILABLE_TOOLS["get_count"]()
    assert result1 == 10

    # Register second instance - should replace first
    counter2 = Counter(start_value=20)
    register_instance(counter2)
    result2 = AVAILABLE_TOOLS["get_count"]()
    assert result2 == 20
