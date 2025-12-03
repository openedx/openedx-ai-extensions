"""Utility functions for Open edX AI Extensions."""

from types import GeneratorType


def is_generator(result):
    """
    Check if the given object is a generator.

    Args:
        result (Any): The object to check.

    Returns:
        bool: True if the object is an instance of GeneratorType, False otherwise.
    """
    return isinstance(result, GeneratorType)
