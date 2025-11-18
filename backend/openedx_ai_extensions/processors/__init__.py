"""
Processors module - handles data extraction and AI processing
"""

from .llm_processor import LLMProcessor
from .openedx_processor import OpenEdXProcessor
from .educator_assistant_processor import EducatorAssistantProcessor

__all__ = ["LLMProcessor", "OpenEdXProcessor", "EducatorAssistantProcessor"]
