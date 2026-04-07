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

    def _stream_and_emit(self, generator):
        """Yield all chunks from the generator, then emit the completed event."""
        try:
            yield from generator
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error in stream wrapper: {e}")
            yield f"\n[Error processing stream: {e}]".encode("utf-8")
        finally:
            try:
                self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Failed to emit workflow event after stream: {e}")

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
        self.llm_processor = LLMProcessor(self.profile.processor_config)
        llm_result = self.llm_processor.process(context=llm_input_content)

        # --- 4. Handle Streaming Response (Generator) ---
        if is_generator(llm_result):
            return self._stream_and_emit(llm_result)

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
        }
        return response_data


class EducatorAssistantOrchestrator(SessionBasedOrchestrator):
    """
    Orchestrator for educator assistant workflows.

    Generates quiz questions and optionally stores them in content libraries.

    Two modes:
    - Direct mode (library_id in input_data): generate + commit immediately (legacy).
    - Iterative mode (no library_id): generate → store in session → review → save separately.
    """

    def _attach_olx(self, problem):
        """Return a copy of problem with an 'olx' key containing its OLX string."""
        try:
            return {**problem, 'olx': json_to_olx(problem)}
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Could not generate OLX for problem: {e}")
            return problem

    @property
    def _schema_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "response_schemas"
            / "educator_quiz_questions.json"
        )

    def _run_openedx_processor(self):
        """Run the OpenEdX processor to fetch course content."""
        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            location_id=self.location_id,
            course_id=self.course_id,
            user=self.user,
        )
        return openedx_processor.process()

    def _run_llm_processor(self, content_result, input_data):
        """Run the LLM processor to generate quiz questions."""
        with open(self._schema_path, 'r', encoding='utf-8') as f:
            self.llm_processor = EducatorAssistantProcessor(
                config=self.profile.processor_config,
                user=self.user,
                context=content_result,
                extra_params={"response_format": json.load(f)}
            )
        result = self.llm_processor.process(input_data=input_data)
        # EducatorAssistantProcessor returns usage in the result dict rather than
        # accumulating it on self.usage, so we sync it here for auto-lookup.
        self.llm_processor.usage = result.get("usage") or None
        return result

    def get_current_session_response(self, _):
        """
        Retrieve the current session state.

        - If a collection was already saved: return the collection URL.
        - If questions were generated but not yet saved: return them for review.
        - Otherwise: return None.
        """
        metadata = self.session.metadata or {}
        if "collection_url" in metadata:
            return {"response": metadata["collection_url"]}
        if "question_slots" in metadata:
            return {
                "response": {
                    "question_slots": metadata["question_slots"],
                    "collection_name": metadata.get("collection_name", ""),
                }
            }
        return {"response": None}

    def run(self, input_data):
        """
        Generate quiz questions.

        If library_id is present in input_data, immediately commit to library (legacy path).
        Otherwise store questions in session metadata for iterative review.
        """
        content_result = self._run_openedx_processor()
        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}

        llm_result = self._run_llm_processor(content_result, input_data)
        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        # Iterative path: store questions for review
        response_payload = llm_result.get("response", {}) or {}
        problems = response_payload.get("problems", []) or []
        collection_name = response_payload.get("collection_name", "AI Generated Questions")

        # Each slot owns its version history; start with one version (the original)
        question_slots = [
            {"versions": [self._attach_olx(p)], "selected": 0}
            for p in problems
        ]

        metadata = self.session.metadata or {}
        metadata['question_slots'] = question_slots
        metadata['collection_name'] = collection_name
        self.session.metadata = metadata
        self.session.save(update_fields=["metadata"])

        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        return {
            'status': 'completed',
            'response': {
                'question_slots': question_slots,
                'collection_name': collection_name,
            }
        }

    def regenerate_question(self, input_data):
        """
        Refine an existing question at the given slot index.

        Uses a dedicated refinement prompt so the LLM improves the provided
        question rather than generating an unrelated new one.
        """
        question_index = input_data.get('question_index')

        content_result = self._run_openedx_processor()
        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}

        metadata = self.session.metadata or {}
        question_slots = metadata.get('question_slots', [])

        if question_index is None or not 0 <= question_index < len(question_slots):
            return {'error': 'Invalid question index', 'status': 'error'}

        slot = question_slots[question_index]
        input_data['existing_question'] = slot['versions'][slot['selected']]

        # Use the dedicated refinement prompt and processor
        with open(self._schema_path, 'r', encoding='utf-8') as f:
            llm_processor = EducatorAssistantProcessor(
                config=self.profile.processor_config,
                user=self.user,
                context=content_result,
                extra_params={"response_format": json.load(f)}
            )

        llm_result = llm_processor.refine_quiz_question(input_data=input_data)
        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        problems = (llm_result.get("response") or {}).get("problems") or []
        if not problems:
            return {'error': 'No question generated', 'status': 'error'}

        new_question = self._attach_olx(problems[0])

        # Append the new version to this slot and select it
        slot['versions'].append(new_question)
        slot['selected'] = len(slot['versions']) - 1

        metadata['question_slots'] = question_slots
        self.session.metadata = metadata
        self.session.save(update_fields=["metadata"])
        return {
            'status': 'completed',
            'response': {
                'question': new_question,
                'history': slot['versions'],
                'selected': slot['selected'],
            },
        }

    def save(self, input_data):
        """
        Commit selected questions to a content library.

        Expects input_data with library_id, questions list, and optional publish flag.
        """
        lib_key_str = input_data.get('library_id')
        questions = input_data.get('questions', [])

        metadata = self.session.metadata or {}
        collection_name = (
            input_data.get('collection_name')
            or metadata.get('collection_name')
            or 'AI Generated Questions'
        )

        items = []
        for problem in questions:
            try:
                olx_content = json_to_olx(problem)
                items.append(olx_content)
            except Exception as e:  # pylint: disable=broad-except
                logger.exception(f"Error converting problem to OLX: {e}")
                continue

        library_processor = ContentLibraryProcessor(
            library_key=lib_key_str,
            user=self.user,
            config=self.profile.processor_config
        )
        collection_key = library_processor.create_collection_and_add_items(
            title=collection_name,
            description="AI-generated quiz questions",
            items=items,
        )

        collection_url = f"authoring/library/{lib_key_str}/collection/{collection_key}"
        metadata['collection_url'] = collection_url
        metadata['library_id'] = lib_key_str
        metadata['collection_id'] = collection_key
        self.session.metadata = metadata
        self.session.save(update_fields=["metadata"])
        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)
        return {
            'status': 'completed',
            'response': collection_url,
        }
