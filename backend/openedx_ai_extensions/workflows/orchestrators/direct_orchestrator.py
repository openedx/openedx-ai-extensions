"""
Orchestrators for handling different AI workflow patterns in Open edX.
"""
import json
import logging
from pathlib import Path

from openedx_ai_extensions.processors import (
    ContentLibraryProcessor,
    EducatorAssistantProcessor,
    LLMProcessor,
    OpenEdXProcessor,
)
from openedx_ai_extensions.processors.openedx.utils.json_to_olx import json_to_olx
from openedx_ai_extensions.utils import is_generator
from openedx_ai_extensions.xapi.constants import EVENT_NAME_WORKFLOW_COMPLETED

from .base_orchestrator import BaseOrchestrator
from .session_based_orchestrator import SessionBasedOrchestrator

logger = logging.getLogger(__name__)


class DirectLLMResponse(BaseOrchestrator):
    """
    Orchestrator for direct LLM responses.
    Does a single call to an LLM and gives a response.
    """

    def run(self, input_data):
        """
        Executes the content fetching, LLM processing, and handles streaming
        or structured response return.
        """

        # --- 1. Process with OpenEdX processor (Content Fetching) ---
        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            location_id=self.location_id,
            course_id=self.course_id,
            user=self.user,
        )
        content_result = openedx_processor.process()

        # Early return on error during content fetching
        if content_result and 'error' in content_result:
            return {
                'error': content_result['error'],
                'status': 'OpenEdXProcessor error'
            }

        # Convert fetched content to a string format suitable for the LLM
        llm_input_content = str(content_result)

        # --- 2. Process with LLM processor ---
        llm_processor = LLMProcessor(self.profile.processor_config)
        llm_result = llm_processor.process(context=llm_input_content)

        # --- 4. Handle Streaming Response (Generator) ---
        if is_generator(llm_result):
            # If the LLM returns a generator, return its directly.
            return llm_result

        # --- 5. Handle LLM Error (Non-Streaming) ---
        if llm_result and 'error' in llm_result:
            # Early return on error during non-streaming LLM processing
            return {
                'error': llm_result['error'],
                'status': 'LLMProcessor error'
            }

        # 6. Emit completed event for one-shot workflow
        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        # --- 7. Return Structured Non-Streaming Result ---
        # If execution reaches this point, we have a successful, non-streaming result (Dict).
        response_data = {
            'response': llm_result.get('response', 'No response available'),
            'status': 'completed',
            'metadata': {
                'tokens_used': llm_result.get('tokens_used'),
                'model_used': llm_result.get('model_used')
            }
        }
        return response_data


class EducatorAssistantOrchestrator(SessionBasedOrchestrator):
    """
    Orchestrator for educator assistant workflows.

    Generates quiz questions and stores them in content libraries.
    """

    def get_current_session_response(self, _):
        """Retrieve the current session's LLM response."""
        metadata = self.session.metadata or {}
        if metadata and "collection_url" in metadata:
            return {"response": metadata["collection_url"]}
        return {"response": None}

    def run(self, input_data):
        # 1. Process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            location_id=self.location_id,
            course_id=self.course_id,
            user=self.user,
        )
        content_result = openedx_processor.process()

        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}

        schema_path = (
            Path(__file__).resolve().parent.parent.parent
            / "response_schemas"
            / "educator_quiz_questions.json"
        )

        # 2. Process with LLM processor using structured output schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            llm_processor = EducatorAssistantProcessor(
                config=self.profile.processor_config,
                user=self.user,
                context=content_result,
                extra_params={"response_format": json.load(f)}
            )
        llm_result = llm_processor.process(input_data=input_data)

        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        items = []
        for problem in llm_result.get("response").get("problems", []):
            try:
                olx_content = json_to_olx(problem)
                items.append(olx_content)
            except Exception as e:  # pylint: disable=broad-except
                logger.exception(f"Error converting problem to OLX: {e}")
                continue

        lib_key_str = input_data.get('library_id')

        library_processor = ContentLibraryProcessor(
            library_key=lib_key_str,
            user=self.user,
            config=self.profile.processor_config
        )

        collection_key = library_processor.create_collection_and_add_items(
            title=llm_result.get("response", {}).get("collection_name", "AI Generated Questions"),
            description="AI-generated quiz questions",
            items=items
        )

        metadata = {
            "library_id": lib_key_str,
            "collection_url": f"authoring/library/{lib_key_str}/collection/{collection_key}",
            "collection_id": collection_key,
        }
        self.session.metadata = metadata
        self.session.save(update_fields=["metadata"])

        # Emit completed event for one-shot workflow
        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        # 4. Return result
        return {
            'response': f"authoring/library/{lib_key_str}/collection/{collection_key}",
            'status': 'completed',
            'metadata': {
                'tokens_used': llm_result.get('tokens_used'),
                'model_used': llm_result.get('model_used')
            }
        }
