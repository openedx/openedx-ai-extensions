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

    Generates quiz questions and optionally stores them in content libraries.

    Two modes:
    - Direct mode (library_id in input_data): generate + commit immediately (legacy).
    - Iterative mode (no library_id): generate → store in session → review → save separately.
    """

    @property
    def _schema_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "response_schemas"
            / "educator_quiz_questions.json"
        )

    def _run_openedx_processor(self):
        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            location_id=self.location_id,
            course_id=self.course_id,
            user=self.user,
        )
        return openedx_processor.process()

    def _run_llm_processor(self, content_result, input_data):
        with open(self._schema_path, 'r', encoding='utf-8') as f:
            llm_processor = EducatorAssistantProcessor(
                config=self.profile.processor_config,
                user=self.user,
                context=content_result,
                extra_params={"response_format": json.load(f)}
            )
        return llm_processor.process(input_data=input_data)

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
        if "questions" in metadata:
            return {
                "response": {
                    "questions": metadata["questions"],
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

        lib_key_str = input_data.get('library_id')

        if lib_key_str:
            # Legacy direct-commit path
            items = []
            for problem in llm_result.get("response", {}).get("problems", []):
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
                title=llm_result.get("response", {}).get("collection_name", "AI Generated Questions"),
                description="AI-generated quiz questions",
                items=items
            )

            self.session.metadata = {
                "library_id": lib_key_str,
                "collection_url": f"authoring/library/{lib_key_str}/collection/{collection_key}",
                "collection_id": collection_key,
            }
            self.session.save(update_fields=["metadata"])
            self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)
            return {
                'response': f"authoring/library/{lib_key_str}/collection/{collection_key}",
                'status': 'completed',
                'metadata': {
                    'tokens_used': llm_result.get('tokens_used'),
                    'model_used': llm_result.get('model_used')
                }
            }

        # Iterative path: store questions for review
        problems = llm_result.get("response", {}).get("problems", [])
        collection_name = llm_result.get("response", {}).get("collection_name", "AI Generated Questions")
        metadata = self.session.metadata or {}
        metadata['questions'] = problems
        metadata['collection_name'] = collection_name
        self.session.metadata = metadata
        self.session.save(update_fields=["metadata"])
        return {
            'status': 'completed',
            'response': {
                'questions': problems,
                'collection_name': collection_name,
            }
        }

    def regenerate_question(self, input_data):
        """
        Refine and replace a single question at the given index.

        Passes the existing question as context so the LLM improves it rather than
        generating an entirely new one. Optional extra_instructions guide the refinement.
        """
        question_index = input_data.get('question_index')
        extra_instructions = input_data.get('extra_instructions', '')

        content_result = self._run_openedx_processor()
        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}

        metadata = self.session.metadata or {}
        existing_questions = metadata.get('questions', [])

        # Build refinement context from the existing question so the LLM improves
        # it rather than generating a brand-new, unrelated question.
        existing_question = (
            existing_questions[question_index]
            if 0 <= (question_index or -1) < len(existing_questions)
            else {}
        )
        refinement_parts = [
            "Refine and improve the following existing question. "
            "Keep the same general topic but improve clarity, distractors, "
            "or pedagogical value as needed.",
            f"\nExisting question to refine:",
            f"  Title: {existing_question.get('display_name', '')}",
            f"  Question text: {existing_question.get('question_html', '')}",
            f"  Problem type: {existing_question.get('problem_type', '')}",
            f" {existing_question}"
        ]
        if extra_instructions:
            refinement_parts.append(f"\nAdditional refinement instructions: {extra_instructions}")

        regen_input = {
            'num_questions': 1,
            'extra_instructions': "\n".join(refinement_parts),
        }
        llm_result = self._run_llm_processor(content_result, regen_input)
        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        problems = llm_result.get("response", {}).get("problems", [])
        if not problems:
            return {'error': 'No question generated', 'status': 'error'}

        new_question = problems[0]
        if 0 <= (question_index or -1) < len(existing_questions):
            existing_questions[question_index] = new_question
        else:
            existing_questions.append(new_question)

        metadata['questions'] = existing_questions
        self.session.metadata = metadata
        self.session.save(update_fields=["metadata"])
        return {
            'status': 'completed',
            'response': new_question,
        }

    def save(self, input_data):
        """
        Commit selected questions to a content library.

        Expects input_data with library_id, questions list, and optional publish flag.
        """
        lib_key_str = input_data.get('library_id')
        questions = input_data.get('questions', [])

        metadata = self.session.metadata or {}
        collection_name = metadata.get('collection_name', 'AI Generated Questions')

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
