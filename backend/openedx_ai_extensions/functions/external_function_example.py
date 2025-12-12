"""
LLM function definitions and utilities for AI-powered workflows.
"""

import logging
import random

from openedx_ai_extensions.functions.decorators import llm_tool

logger = logging.getLogger(__name__)


@llm_tool(schema={
    "name": "roll_dice",
    "description": "Simulate rolling a specified number of six-sided dice",
    "parameters": {
        "type": "object",
        "properties": {
            "n_dice": {
                "type": "integer",
                "description": "The number of dice to roll",
                "default": 1
            }
        }
    }
})
def roll_dice(n_dice=1, **kwargs):
    """Simulate rolling a specified number of six-sided dice."""
    roll = [random.randint(1, 6) for _ in range(n_dice)]
    return roll
