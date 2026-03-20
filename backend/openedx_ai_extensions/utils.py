"""
Utility functions for Open edX AI Extensions.
"""

from types import GeneratorType

# Standardized error message for mid-stream failures.
# This MUST match the frontend's ERROR_MESSAGES.streaming_failed for consistency.
STREAMING_FAILED_MESSAGE = "The AI service encountered an error while generating the response. Please try again."


def normalize_input_to_text(input_data) -> str:
    """
    Coerce input_data to a plain string suitable for use as message content.

    Handles: str, dict with 'text' key, other dicts (JSON-serialised), None.
    """
    if isinstance(input_data, str):
        return input_data
    if isinstance(input_data, dict):
        return input_data.get("text") or ""
    if input_data is None:
        return ""
    return str(input_data)


def is_generator(result):
    """
    Check if the given object is a generator.

    Args:
        result (Any): The object to check.

    Returns:
        bool: True if the object is an instance of GeneratorType, False otherwise.
    """
    return isinstance(result, GeneratorType)
