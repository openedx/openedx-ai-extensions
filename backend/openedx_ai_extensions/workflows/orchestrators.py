"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""

from openedx_ai_extensions.processors import CompletionLLMProcessor, OpenEdXProcessor, MCPLLMProcessor
import logging

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

        context = f"""
        course_id: {self.workflow.course_id}
        unit_id: {self.workflow.extra_context.get('unitId')}
        """

        # 2. Process with MCPLLMProcessor
        llm_processor = MCPLLMProcessor(self.config.processor_config)
        llm_result = llm_processor.process(context)

        if "error" in llm_result:
            return {"error": llm_result["error"], "status": "MCPLLMProcessor error"}

        # 3. Return result
        return {
            "response": llm_result.get("response", "No response available"),
            "status": "completed",
            "metadata": {
                "tokens_used": llm_result.get("tokens_used"),
                "model_used": llm_result.get("model_used"),
            },
        }
