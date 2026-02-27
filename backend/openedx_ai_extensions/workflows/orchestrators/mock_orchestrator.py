"""
Mock orchestrator for testing and development.
"""
import logging
import time

from openedx_ai_extensions.xapi.constants import EVENT_NAME_WORKFLOW_COMPLETED

from .base_orchestrator import BaseOrchestrator

logger = logging.getLogger(__name__)


class MockResponse(BaseOrchestrator):
    """
    Complete mock orchestrator.
    Responds inmediately with a mock answer. Useful for UI testing.
    """

    def run(self, input_data):
        # Emit completed event for one-shot workflow
        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        return {
            "response": f"Mock response for {self.workflow.action} at {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "status": "completed",
        }


class MockStreamResponse(BaseOrchestrator):
    """
    Complete mock orchestrator with streaming.
    Responds inmediately with a mock answer in a streaming fashion. Useful for UI testing.
    """

    def run(self, input_data):
        # Emit completed event for one-shot workflow
        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        def stream_generator():
            mock_response = (
                "This streaming function emits incremental chunks of data as they become available, "
                "rather than waiting for the full response to be computed. It is designed for low-latency, "
                "real-time consumption, allowing callers to process partial results immediately. Each yielded "
                "event represents a discrete update in the stream and may contain content, metadata, "
                "or control signals.The stream remains open until completion or error, at which point "
                "it is gracefully closed. Consumers are expected to iterate over the stream sequentially "
                "and handle partial data, retries, or early termination as needed."
            )
            chunk_size = 15
            for i in range(0, len(mock_response), chunk_size):
                time.sleep(0.01)
                yield mock_response[i:i + chunk_size].encode("utf-8")

        return stream_generator()
