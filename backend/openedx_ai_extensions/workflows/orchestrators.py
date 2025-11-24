"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""

import logging
from typing import TYPE_CHECKING

from openedx_ai_extensions.processors import LLMProcessor, OpenEdXProcessor, ResponsesProcessor, SubmissionProcessor

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
            "course_id": self.workflow.course_id,
            "extra_context": self.workflow.extra_context,
        }

        # 1. Process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_result = openedx_processor.process(context)

        if "error" in content_result:
            return {
                "error": content_result["error"],
                "status": "OpenEdXProcessor error",
            }

        # 2. Process with LLM processor
        llm_processor = LLMProcessor(self.config.processor_config)
        llm_result = llm_processor.process(str(content_result))

        if "error" in llm_result:
            return {"error": llm_result["error"], "status": "LLMProcessor error"}

        # 3. Return result
        return {
            "response": llm_result.get("response", "No response available"),
            "status": "completed",
            "metadata": {
                "tokens_used": llm_result.get("tokens_used"),
                "model_used": llm_result.get("model_used"),
            },
        }


class ThreadedLLMResponse(BaseOrchestrator):
    """Orchestrator that provides LLM responses using threading (placeholder)."""

    def run(self, input_data):
        # Prepare context
        from openedx_ai_extensions.workflows.models import AIWorkflowSession  # pylint: disable=import-outside-toplevel

        context = {
            "course_id": self.workflow.course_id,
            "extra_context": self.workflow.extra_context,
        }

        session, _ = AIWorkflowSession.objects.get_or_create(
            user=self.workflow.user,
            course_id=self.workflow.course_id,
            location_id=self.workflow.location_id,
            defaults={},
        )

        # 0. If action = "clear_session", just remove session and return
        if self.workflow.action == "clear_session":
            session.delete()
            return {
                "response": "",
                "status": "session_cleared",
            }

        # 1. get chat history if there is user session
        submission_processor = SubmissionProcessor(
            self.config.processor_config, session
        )
        if session and session.local_submission_id and not input_data:
            history_result = submission_processor.process(context)

            if "error" in history_result:
                return {
                    "error": history_result["error"],
                    "status": "SubmissionProcessor error",
                }
            return {
                "response": history_result.get("response", "No response available"),
                "status": "completed"
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
        llm_processor = ResponsesProcessor(self.config.processor_config, session)
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
