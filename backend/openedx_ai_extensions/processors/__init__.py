"""
Processors module - handles data extraction and AI processing
"""

from .llm_processor import LLMProcessor
from .openedx_processor import OpenEdXProcessor

__all__ = ["LLMProcessor", "OpenEdXProcessor"]
