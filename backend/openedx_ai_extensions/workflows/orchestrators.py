"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""
import json
import logging
from typing import TYPE_CHECKING

from openedx_ai_extensions.processors import (
    EducatorAssistantProcessor,
    LLMProcessor,
    OpenEdXProcessor,
    ResponsesProcessor,
    SubmissionProcessor,
)

if TYPE_CHECKING:
    from openedx_ai_extensions.workflows.models import AIWorkflowSession

logger = logging.getLogger(__name__)


class BaseOrchestrator:
    """Base class for workflow orchestrators."""

    def __init__(self, workflow):
        self.workflow = workflow
        self.config = workflow.config

    def run(self, input_data):
        raise NotImplementedError("Subclasses must implement run method")


class MockResponse(BaseOrchestrator):
    def run(self, input_data):
        return {
            "response": f"Mock response for {self.workflow.action}",
            "status": "completed",
        }


class DirectLLMResponse(BaseOrchestrator):
    """Orchestrator that provides direct LLM responses."""

    def run(self, input_data):
        # Prepare context
        context = {
            'course_id': self.workflow.course_id,
            'extra_context': self.workflow.extra_context
        }

        # 1. Process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_result = openedx_processor.process(context)

        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}

        # 2. Process with LLM processor
        llm_processor = LLMProcessor(self.config.processor_config)
        llm_result = llm_processor.process(str(content_result))

        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        # 3. Return result
        return {
            'response': llm_result.get('response', 'No response available'),
            'status': 'completed',
            'metadata': {
                'tokens_used': llm_result.get('tokens_used'),
                'model_used': llm_result.get('model_used')
            }
        }


class EducatorAssistantOrchestrator(BaseOrchestrator):
    """Orchestrator for educator assistant workflows."""

    def run(self, input_data):
        # Prepare context
        context = {
            'course_id': self.workflow.course_id,
            'extra_context': self.workflow.extra_context
        }

        # 1. Process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_result = openedx_processor.process(context)

        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}

        # 2. Process with LLM processor
        llm_processor = EducatorAssistantProcessor(
            config=self.config.processor_config,
            user=self.workflow.user,
            context=content_result
        )
        llm_result = llm_processor.process(input_data)

        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        # 3. Return result
        return {
            'response': llm_result.get('response', 'No response available'),
            'status': 'completed',
            'metadata': {
                'tokens_used': llm_result.get('tokens_used'),
                'model_used': llm_result.get('model_used')
            }
        }


class ThreadedLLMResponse(BaseOrchestrator):
    """Orchestrator that provides LLM responses using threading (placeholder)."""

    def __init__(self, workflow):
        from openedx_ai_extensions.workflows.models import AIWorkflowSession  # pylint: disable=import-outside-toplevel

        super().__init__(workflow)
        self.session, _ = AIWorkflowSession.objects.get_or_create(
            user=self.workflow.user,
            course_id=self.workflow.course_id,
            location_id=self.workflow.location_id,
            defaults={},
        )

    def clear_session(self, _):
        self.session.delete()
        return {
            "response": "",
            "status": "session_cleared",
        }

    def lazy_load_chat_history(self, input_data):
        """
        Load older messages for infinite scroll.
        Expects input_data to contain current_messages (count) from frontend.
        Returns only new messages not already loaded, limited by max_context_messages.
        """
        submission_processor = SubmissionProcessor(
            self.config.processor_config, self.session
        )

        # Extract current_messages_count from input_data
        current_messages_count = 0
        if isinstance(input_data, dict):
            current_messages_count = input_data.get("current_messages", 0)
        elif isinstance(input_data, str):
            try:
                parsed_data = json.loads(input_data)
                current_messages_count = parsed_data.get("current_messages", 0)
            except (json.JSONDecodeError, AttributeError):
                current_messages_count = 0
        elif isinstance(input_data, int):
            current_messages_count = input_data

        result = submission_processor.get_previous_messages(current_messages_count)

        if "error" in result:
            return {
                "error": result["error"],
                "status": "error",
            }

        return {
            "response": result.get("response", "{}"),
            "status": "completed",
        }

    def run(self, input_data):
        context = {
            "course_id": self.workflow.course_id,
            "extra_context": self.workflow.extra_context,
        }

        # 1. get chat history if there is user session
        submission_processor = SubmissionProcessor(
            self.config.processor_config, self.session
        )
        if self.session and self.session.local_submission_id and not input_data:
            history_result = submission_processor.process(context)

            if "error" in history_result:
                return {
                    "error": history_result["error"],
                    "status": "SubmissionProcessor error",
                }
            return {
                "response": history_result.get("response", "No response available"),
                "status": "completed",
            }

        # 2. else process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_result = openedx_processor.process(context=context)

        if "error" in content_result:
            return {
                "error": content_result["error"],
                "status": "OpenEdXProcessor error",
            }

        # 3. Process with LLM processor
        llm_processor = ResponsesProcessor(self.config.processor_config, self.session)
        llm_result = llm_processor.process(
            context=str(content_result), input_data=input_data
        )

        submission_processor.update_submission(llm_result.get("response"), input_data)

        if "error" in llm_result:
            return {"error": llm_result["error"], "status": "ResponsesProcessor error"}

        # 3. Return result
        return {
            "response": llm_result.get("response", "No response available"),
            "status": "completed",
            "metadata": {
                "tokens_used": llm_result.get("tokens_used"),
                "model_used": llm_result.get("model_used"),
            },
        }
