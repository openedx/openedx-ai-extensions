"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""
import json
import logging

from openedx_ai_extensions.processors import LLMProcessor, OpenEdXProcessor
from openedx_ai_extensions.utils import is_generator
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
        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            location_id=self.location_id,
            course_id=self.course_id,
            user=self.user,
        )
        content_result = openedx_processor.process()

        if "error" in content_result:
            return {
                "error": content_result["error"],
                "status": "OpenEdXProcessor error",
            }

        # 3. Process with LLM processor
        llm_processor = LLMProcessor(self.profile.processor_config, self.session)

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
