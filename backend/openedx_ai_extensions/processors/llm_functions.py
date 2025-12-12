"""
LLM function definitions and utilities for AI-powered workflows.
"""

import inspect
import logging
import random

import litellm

from openedx_ai_extensions.processors.openedx.openedx_processor import OpenEdXProcessor

logger = logging.getLogger(__name__)


def get_location_content(location_id, **kwargs):
    """Get the content of a given Open edX location.

    Parameters
    ----------
    location_id : str
        The string representation of the location ID.

    Returns
    -------
    str
        The extracted content from the specified location.
    """
    try:
        openedx_processor = OpenEdXProcessor()
        return openedx_processor.get_location_content(location_id)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error extracting content for location {location_id}: {e}")
        return ""


def roll_dice(n_dice=1, **kwargs):
    """Simulate rolling a specified number of six-sided dice.

    Parameters
    ----------
    n_dice : int
        The number of dice to roll.
    Returns
    -------
    list of int
        A list containing the results of each die roll.
    """
    roll = [random.randint(1, 6) for _ in range(n_dice)]
    return roll


AVAILABLE_FUNCTIONS = {
    name: obj
    for name, obj in globals().items()
    if inspect.isfunction(obj) and obj.__module__ == __name__
}

FUNCTIONS_SCHEMA = {
    name: litellm.utils.function_to_dict(obj)
    for name, obj in AVAILABLE_FUNCTIONS.items()
}
