"""
LLM function definitions and utilities for AI-powered workflows.
"""

import inspect
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Registry to store decorated functions
_LLM_FUNCTION_REGISTRY = {}
# Registry to store function schemas
_LLM_SCHEMA_REGISTRY = {}
# Registry to store instances by class name for methods
_LLM_CLASS_INSTANCES = {}


def register_instance(instance):
    """
    Register a class instance to make its decorated methods available.

    This should be called when a class with @llm_tool decorated methods
    is instantiated and you want those methods to be callable via AVAILABLE_TOOLS.

    Args:
        instance: The class instance to register

    Example:
        processor = OpenEdXProcessor(config)
        register_instance(processor)
    """
    class_name = instance.__class__.__name__
    _LLM_CLASS_INSTANCES[class_name] = instance


def llm_tool(schema):
    """
    Decorator to register a function as an LLM function.

    This decorator can be applied to both regular functions and instance methods.
    For methods, the instance must be registered using ``register_instance()``
    before the method can be called via ``AVAILABLE_TOOLS``.

    Parameters
    ----------
    schema : dict
        JSON schema for the function.

    Examples
    --------
    Regular function example::

        @llm_tool(
            schema={
                "name": "my_function",
                "description": "Function description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "..."
                        }
                    },
                    "required": ["param1"]
                }
            }
        )
        def my_function(param1):
            \"\"\"Function description.\"\"\"
            return result

    Instance method example::

        class MyClass:
            @llm_tool(schema={...})
            def my_method(self, param1):
                \"\"\"Method description.\"\"\"
                return result

    Registering the instance::

        my_instance = MyClass()
        register_instance(my_instance)
    """
    def decorator(func):
        # Check if this is a method (has 'self' as first parameter)
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        is_method = len(params) > 0 and params[0] == 'self'

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Create a callable that handles both functions and methods
        if is_method:
            # Store the class name for later lookup
            wrapper.is_llm_method = True
            wrapper.original_func = func

            def callable_wrapper(*args, **kwargs):
                """Wrapper that automatically binds the method to its instance."""
                # The qualname includes the class name, e.g., "MyClass.my_method"
                qualname_parts = func.__qualname__.split('.')
                if len(qualname_parts) >= 2:
                    class_name = qualname_parts[-2]

                    if class_name in _LLM_CLASS_INSTANCES:
                        instance = _LLM_CLASS_INSTANCES[class_name]
                        return func(instance, *args, **kwargs)

                    raise RuntimeError(
                        f"Method {func.__name__} from class {class_name} has not been initialized. "
                        f"Call register_instance() with an instance of {class_name} first."
                    )

                raise RuntimeError(
                    f"Could not determine class name for method {func.__name__}"
                    )

            # Register the callable wrapper
            _LLM_FUNCTION_REGISTRY[func.__name__] = callable_wrapper
        else:
            # For regular functions, register as-is
            _LLM_FUNCTION_REGISTRY[func.__name__] = wrapper

        # Register the schema
        _LLM_SCHEMA_REGISTRY[func.__name__] = schema

        return wrapper

    return decorator


# Automatically populated from decorated functions
AVAILABLE_TOOLS = _LLM_FUNCTION_REGISTRY

# Use decorator-provided schemas or auto-generated ones
TOOLS_SCHEMA = _LLM_SCHEMA_REGISTRY
