"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""
import json
import logging
from typing import TYPE_CHECKING

from openedx_ai_extensions.processors import (
    ContentLibraryProcessor,
    EducatorAssistantProcessor,
    LLMProcessor,
    OpenEdXProcessor,
    SubmissionProcessor,
)
from eventtracking import tracker

from openedx_ai_extensions.utils import is_generator
from openedx_ai_extensions.xapi.constants import (
    EVENT_NAME_WORKFLOW_COMPLETED,
    EVENT_NAME_WORKFLOW_INITIALIZED,
    EVENT_NAME_WORKFLOW_INTERACTED,
)

if TYPE_CHECKING:
    from openedx_ai_extensions.workflows.models import AIWorkflowSession

logger = logging.getLogger(__name__)


class BaseOrchestrator:
    """Base class for workflow orchestrators."""

    def __init__(self, workflow):
        self.workflow = workflow
        self.config = workflow.config
        self.location_id = str(workflow.location_id) if workflow.location_id else None

    def _emit_workflow_event(self, event_name: str):
        """
        Emit an xAPI event for this workflow.

        Args:
            event_name: The event name constant (e.g., EVENT_NAME_WORKFLOW_COMPLETED)
        """
        config_filename = self.config.processor_config.get("_config_filename", self.workflow.action)
        workflow_id = f"{config_filename}__{self.workflow.action}"

        tracker.emit(event_name, {
            "workflow_id": workflow_id,
            "action": self.workflow.action,
            "course_id": self.workflow.course_id,
            "workflow_name": config_filename,
            "location_id": self.location_id,
        })

    def run(self, input_data):
        raise NotImplementedError("Subclasses must implement run method")


class MockResponse(BaseOrchestrator):
    """One-shot mock orchestrator - emits completed events."""

    def run(self, input_data):
        # Emit completed event for one-shot workflow
        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        return {
            "response": f"Mock response for {self.workflow.action}",
            "status": "completed",
        }


class DirectLLMResponse(BaseOrchestrator):
    """One-shot orchestrator for direct LLM responses - emits completed events."""

    def run(self, input_data):
        """
        Executes the content fetching, LLM processing, and handles streaming
        or structured response return.
        """

        # --- 1. Process with OpenEdX processor (Content Fetching) ---
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_result = openedx_processor.process(location_id=self.location_id)

        # Early return on error during content fetching
        if content_result and 'error' in content_result:
            return {
                'error': content_result['error'],
                'status': 'OpenEdXProcessor error'
            }

        # Convert fetched content to a string format suitable for the LLM
        llm_input_content = str(content_result)

        # --- 2. Process with LLM processor ---
        llm_processor = LLMProcessor(self.config.processor_config)
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


class SessionBasedOrchestrator(BaseOrchestrator):
    """Orchestrator that provides session-based LLM responses."""

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

    def _get_submission_processor(self):
        return SubmissionProcessor(
            self.config.processor_config, self.session
        )

    def run(self, input_data):
        raise NotImplementedError("Subclasses must implement run method")


class EducatorAssistantOrchestrator(SessionBasedOrchestrator):
    """
    One-shot orchestrator for educator assistant workflows.

    Generates quiz questions and stores them in content libraries.
    Emits completed events.
    """

    def get_current_session_response(self, _):
        """Retrieve the current session's LLM response."""
        metadata = self.session.metadata or {}
        if metadata and "collection_url" in metadata:
            return {"response": metadata["collection_url"]}
        return {"response": None}

    def run(self, input_data):
        # 1. Process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(self.config.processor_config)
        content_result = openedx_processor.process(location_id=self.location_id)

        if 'error' in content_result:
            return {'error': content_result['error'], 'status': 'OpenEdXProcessor error'}

        # 2. Process with LLM processor
        llm_processor = EducatorAssistantProcessor(
            config=self.config.processor_config,
            user=self.workflow.user,
            context=content_result
        )
        llm_result = llm_processor.process(input_data=input_data)

        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        lib_key_str = input_data.get('library_id')

        library_processor = ContentLibraryProcessor(
            library_key=lib_key_str,
            user=self.workflow.user,
            config=self.config.processor_config
        )

        collection_key = library_processor.create_collection_and_add_items(
            title=llm_result["response"].get("collection", "AI Generated Questions"),
            description="AI-generated quiz questions",
            items=llm_result["response"]["items"]
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


class ThreadedLLMResponse(SessionBasedOrchestrator):
    """
    Threaded orchestrator for conversational workflows.

    Emits:
    - initialized: First interaction (no previous session data)
    - interacted: Subsequent interactions (has session/chat history)
    """

    def lazy_load_chat_history(self, input_data):
        """
        Load older messages for infinite scroll.
        Expects input_data to contain current_messages (count) from frontend.
        Returns only new messages not already loaded, limited by max_context_messages.
        """

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

        submission_processor = self._get_submission_processor()
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

    def _stream_and_save_history(self, generator, input_data,  # pylint: disable=too-many-positional-arguments
                                 submission_processor, llm_processor,
                                 initial_system_msgs=None):
        """
        Yields chunks to the view while accumulating text to save to DB
        once the stream finishes.
        """
        full_response_text = []

        try:
            # 1. Iterate and Yield (Streaming Phase)
            for chunk in generator:
                # chunk is bytes (encoded utf-8) from processor
                if isinstance(chunk, bytes):
                    text_chunk = chunk.decode("utf-8", errors="ignore")
                else:
                    text_chunk = str(chunk)

                full_response_text.append(text_chunk)
                yield chunk

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error in stream wrapper: {e}")
            yield f"\n[Error processing stream: {e}]".encode("utf-8")

        finally:
            # 2. Save History (Post-Stream Phase)
            # This executes after the view has consumed the last chunk
            final_response = "".join(full_response_text)

            messages = [
                {"role": "user", "content": input_data},
                {"role": "assistant", "content": final_response},
            ]

            # Re-inject system messages if this was a new thread (and not OpenAI)
            if llm_processor.get_provider() != "openai" and initial_system_msgs:
                for msg in initial_system_msgs:
                    messages.insert(0, {"role": msg["role"], "content": msg["content"]})

            try:
                submission_processor.update_chat_submission(messages)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Failed to save chat history after stream: {e}")

    def run(self, input_data):
        context = {
            'course_id': self.workflow.course_id,
            'location_id': self.location_id,
        }
        submission_processor = self._get_submission_processor()

        # Determine if this is first interaction or subsequent
        has_previous_session = self.session and self.session.local_submission_id
        is_first_interaction = not has_previous_session

        # 1. get chat history if there is user session
        if has_previous_session and not input_data:
            history_result = submission_processor.process(context=context)

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
        content_result = openedx_processor.process(location_id=self.location_id)

        if "error" in content_result:
            return {
                "error": content_result["error"],
                "status": "OpenEdXProcessor error",
            }

        # 3. Process with LLM processor
        llm_processor = LLMProcessor(self.config.processor_config, self.session)

        chat_history = []
        if llm_processor.get_provider() != "openai":
            chat_history = submission_processor.get_full_message_history()

        # Call the processor
        llm_result = llm_processor.process(
            context=str(content_result), input_data=input_data, chat_history=chat_history
        )

        # --- BRANCH A: Handle Streaming (Generator) ---
        if is_generator(llm_result):
            return self._stream_and_save_history(
                generator=llm_result,
                input_data=input_data,
                submission_processor=submission_processor,
                llm_processor=llm_processor,
                initial_system_msgs=None
            )

        # --- BRANCH B: Handle Error ---
        if "error" in llm_result:
            return {"error": llm_result["error"], "status": "ResponsesProcessor error"}

        # --- BRANCH C: Handle Non-Streaming (Standard) ---
        messages = [
            {"role": "assistant", "content": llm_result.get("response", "")},
        ]
        if input_data:
            messages.insert(0, {"role": "user", "content": input_data})

        if llm_processor.get_provider() != "openai":
            system_messages = llm_result.get("system_messages", {})
            for msg in system_messages:
                messages.insert(0, {"role": msg["role"], "content": msg["content"]})

        submission_processor.update_chat_submission(messages)

        if "error" in llm_result:
            return {"error": llm_result["error"], "status": "LLMProcessor error"}

        # Emit appropriate event based on interaction state
        if is_first_interaction:
            self._emit_workflow_event(EVENT_NAME_WORKFLOW_INITIALIZED)
        else:
            self._emit_workflow_event(EVENT_NAME_WORKFLOW_INTERACTED)

        # 4. Return result
        return {
            "response": llm_result.get("response", "No response available"),
            "status": "completed",
            "metadata": {
                "tokens_used": llm_result.get("tokens_used"),
                "model_used": llm_result.get("model_used"),
            },
        }
