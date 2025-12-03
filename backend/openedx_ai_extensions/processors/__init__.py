"""
Processors module - handles data extraction and AI processing
"""

from .completion_processor import CompletionProcessor
from .educator_assistant_processor import EducatorAssistantProcessor
from .openedx.content_libraries_processor import ContentLibraryProcessor
from .openedx.openedx_processor import OpenEdXProcessor
from .openedx.submission_processor import SubmissionProcessor
from .responses_processor import ResponsesProcessor

__all__ = [
    "ContentLibraryProcessor",
    "CompletionProcessor",
    "OpenEdXProcessor",
    "ResponsesProcessor",
    "SubmissionProcessor",
    "EducatorAssistantProcessor"
]
