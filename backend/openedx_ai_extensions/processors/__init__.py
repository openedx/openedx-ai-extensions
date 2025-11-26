"""
Processors module - handles data extraction and AI processing
"""

from .educator_assistant_processor import EducatorAssistantProcessor
from .llm_processor import LLMProcessor
from .openedx.openedx_processor import OpenEdXProcessor
from .openedx.submission_processor import SubmissionProcessor
from .responses_processor import ResponsesProcessor

__all__ = [
    "LLMProcessor",
    "OpenEdXProcessor",
    "ResponsesProcessor",
    "SubmissionProcessor",
    "EducatorAssistantProcessor"
]
