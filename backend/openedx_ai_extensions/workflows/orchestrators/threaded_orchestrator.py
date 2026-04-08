"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""
import json
import logging
import re

from openedx_ai_extensions.processors import LLMProcessor, OpenEdXProcessor
from openedx_ai_extensions.utils import STREAMING_FAILED_MESSAGE, is_generator, normalize_input_to_text
from openedx_ai_extensions.xapi.constants import EVENT_NAME_WORKFLOW_INITIALIZED, EVENT_NAME_WORKFLOW_INTERACTED

from .session_based_orchestrator import SessionBasedOrchestrator

logger = logging.getLogger(__name__)


class ThreadedLLMResponse(SessionBasedOrchestrator):
    """
    Threaded orchestrator for conversational workflows.
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
            "response": result.get("response") or "{}",
            "status": "completed",
        }

    def _stream_and_save_history(self, generator, input_data,  # pylint: disable=too-many-positional-arguments
                                 submission_processor,
                                 initial_system_msgs=None, is_first_interaction=False):
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
            error_marker = json.dumps({
                "error_in_stream": True,
                "code": "streaming_failed",
                "message": STREAMING_FAILED_MESSAGE
            })
            yield f"||{error_marker}||".encode("utf-8")

        finally:
            # 2. Save History (Post-Stream Phase)
            # This executes after the view has consumed the last chunk
            final_response = "".join(full_response_text)

            if "||{\"error_in_stream\":" in final_response:
                # Target specifically the error-in-stream JSON marker
                final_response = re.sub(
                    r"\|\|\{\"error_in_stream\":\s*true,.*?\}\|\|",
                    f"\n\n{STREAMING_FAILED_MESSAGE}",
                    final_response
                )

            user_text = normalize_input_to_text(input_data)

            messages = [{"role": "assistant", "content": final_response}]
            if user_text:
                messages.insert(0, {"role": "user", "content": user_text})

            # Re-inject system messages if this was a new thread (and not OpenAI)
            if self.llm_processor.get_provider() != "openai" and initial_system_msgs:
                for msg in initial_system_msgs:
                    messages.insert(0, {"role": msg["role"], "conte{}nt": msg["content"]})

            try:
                submission_processor.update_chat_submission(messages)
                if is_first_interaction:
                    self._emit_workflow_event(EVENT_NAME_WORKFLOW_INITIALIZED)
                else:
                    self._emit_workflow_event(EVENT_NAME_WORKFLOW_INTERACTED)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Failed to save chat history after stream: {e}")

    def run(self, input_data):
        context = {
            'course_id': self.course_id,
            'location_id': self.location_id,
        }
        submission_processor = self._get_submission_processor()

        # Determine if this is first interaction or subsequent
        has_previous_session = self.session and self.session.local_submission_id
        is_first_interaction = not has_previous_session

        # 1. get chat history if there is user session
        if has_previous_session and not input_data:
            history_result = submission_processor.process(context=context)
            return {
                "response": history_result.get("response") or "No response available",
                "status": "completed",
            }

        # 2. else process with OpenEdX processor
        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            location_id=self.location_id,
            course_id=self.course_id,
            user=self.user,
        )
        content_result = openedx_processor.process()

        # 3. Process with LLM processor
        self.llm_processor = LLMProcessor(self.profile.processor_config, self.session)

        # Only fetch history if we don't have a remote thread ID.
        # This reduces DB + JSON overhead on every request.
        # Fallback (self-healing) is handled via lazy-fetching or explicit retry if needed.
        has_remote_id = bool(self.session and self.session.remote_response_id)
        chat_history = []
        if not has_remote_id:
            chat_history = submission_processor.get_full_message_history() or []

        # Call the processor
        llm_result = self.llm_processor.process(
            context=str(content_result), input_data=input_data, chat_history=chat_history
        )

        # --- BRANCH A: Handle Streaming (Generator) ---
        if is_generator(llm_result):
            return self._stream_and_save_history(
                generator=llm_result,
                input_data=input_data,
                submission_processor=submission_processor,
                initial_system_msgs=None,
                is_first_interaction=is_first_interaction,
            )

        # --- BRANCH B: Handle Non-Streaming (Standard) ---
        messages = [
            {"role": "assistant", "content": llm_result.get("response") or ""},
        ]
        user_text = normalize_input_to_text(input_data)
        if user_text:
            messages.insert(0, {"role": "user", "content": user_text})

        # Save system messages (if present) so they are available in local history
        # for fallback if remote threading is lost.
        system_messages = llm_result.get("system_messages", [])
        for msg in reversed(system_messages):
            messages.insert(0, {"role": msg["role"], "content": msg["content"]})

        submission_processor.update_chat_submission(messages)

        # Emit appropriate event based on interaction state
        if is_first_interaction:
            self._emit_workflow_event(EVENT_NAME_WORKFLOW_INITIALIZED)
        else:
            self._emit_workflow_event(EVENT_NAME_WORKFLOW_INTERACTED)

        # 4. Return result
        return {
            "response": llm_result.get("response") or "No response available",
            "status": "completed",
        }
