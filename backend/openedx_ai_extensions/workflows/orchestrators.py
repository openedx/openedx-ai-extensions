"""
Orchestrators
Base classes to hold the logic of execution in ai workflows
"""
import json
import logging
import sys
import time
from typing import TYPE_CHECKING

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from eventtracking import tracker

from openedx_ai_extensions.processors import (
    ContentLibraryProcessor,
    EducatorAssistantProcessor,
    LLMProcessor,
    OpenEdXProcessor,
    SubmissionProcessor,
)
from openedx_ai_extensions.utils import is_generator
from openedx_ai_extensions.xapi.constants import (
    EVENT_NAME_WORKFLOW_COMPLETED,
    EVENT_NAME_WORKFLOW_INITIALIZED,
    EVENT_NAME_WORKFLOW_INTERACTED,
)

if TYPE_CHECKING:
    from openedx_ai_extensions.workflows.models import AIWorkflow, AIWorkflowSession

logger = logging.getLogger(__name__)


@shared_task(
    name="openedx_ai_extensions.workflows.execute_orchestrator",
    bind=True,
    time_limit=300,
    soft_time_limit=270
)
def _execute_orchestrator_async(task_self, session_id, action, params=None):
    """
    Execute an orchestrator action asynchronously.

    Args:
        task_self: Celery task instance (bound)
        session_id: UUID of the AIWorkflowSession
        action: Method name to call on the orchestrator (e.g., 'run')
        params: Dictionary of parameters to pass to the action method

    Returns:
        Result from the orchestrator action method
    """
    from openedx_ai_extensions.workflows.models import AIWorkflowSession  # pylint: disable=import-outside-toplevel

    task_id = task_self.request.id
    params = params or {}

    try:
        # 1. Get the session from the database
        session = AIWorkflowSession.objects.select_related('scope', 'profile', 'user').get(id=session_id)

        # 2. Build context from session
        context = {
            'course_id': str(session.course_id),
            'location_id': str(session.location_id),
        }

        # 3. Resolve and instantiate orchestrator via centralized factory
        orchestrator_name = session.profile.orchestrator_class
        try:
            orchestrator = BaseOrchestrator.get_orchestrator(
                workflow=session.scope,
                user=session.user,
                context=context,
            )
        except (AttributeError, TypeError) as exc:
            logger.error(
                f"Task {task_id}: Failed to resolve orchestrator: {exc}",
                exc_info=True,
            )
            raise

        # 4. Validate action exists
        if not hasattr(orchestrator, action):
            error_msg = f"Orchestrator '{orchestrator_name}' does not have method '{action}'"
            logger.error(f"Task {task_id}: {error_msg}")
            raise AttributeError(error_msg)

        # 5. Call the action method with params
        orchestrator_method = getattr(orchestrator, action)
        logger.info(f"Task {task_id}: Executing {orchestrator_name}.{action} for session {session_id}")
        result = orchestrator_method(**params)

        # 6. Update session metadata with result
        session.metadata['task_result'] = result
        session.metadata['task_status'] = 'completed'
        session.save(update_fields=['metadata'])

        logger.info(f"Task {task_id}: Completed successfully")
        return result

    except SoftTimeLimitExceeded:
        logger.error(f"Task {task_id}: Soft time limit exceeded for session {session_id}")
        session.metadata['task_status'] = 'timeout'
        session.metadata['task_error'] = 'Task exceeded time limit'
        session.save(update_fields=['metadata'])
        raise

    except AIWorkflowSession.DoesNotExist:
        logger.error(f"Task {task_id}: Session {session_id} not found")
        raise

    except Exception as e:
        logger.error(f"Task {task_id}: Error executing {action} for session {session_id}: {str(e)}")
        session.metadata['task_status'] = 'error'
        session.metadata['task_error'] = str(e)
        session.save(update_fields=['metadata'])
        raise


class BaseOrchestrator:
    """Base class for workflow orchestrators."""

    def __init__(self, workflow, user, context):
        self.workflow = workflow
        self.user = user
        self.profile = workflow.profile
        self.location_id = context.get("location_id", None)
        self.course_id = context.get("course_id", None)

    def _emit_workflow_event(self, event_name: str) -> None:
        """
        Emit an xAPI event for this workflow.

        Args:
            event_name: The event name constant (e.g., EVENT_NAME_WORKFLOW_COMPLETED)
        """

        tracker.emit(event_name, {
            "workflow_id": str(self.workflow.id),
            "action": self.workflow.action,
            "course_id": str(self.course_id),
            "profile_name": self.profile.slug,
            "location_id": str(self.location_id),
        })

    def run(self, input_data):
        raise NotImplementedError("Subclasses must implement run method")

    @classmethod
    def get_orchestrator(cls, *, workflow, user, context):
        """
        Resolve and instantiate an orchestrator for the given workflow.

        This factory method centralizes orchestrator lookup and validation.
        It ensures that the resolved class exists and is a subclass of
        BaseOrchestrator, providing a single, consistent entry point
        for orchestrator creation across the codebase.

        Args:
            workflow: AIWorkflowScope instance that defines the workflow configuration.
            user: User for whom the workflow is being executed.
            context: Dictionary with runtime context (e.g. course_id, location_id).

        Returns:
            BaseOrchestrator: An instantiated orchestrator for the given workflow.

        Raises:
            AttributeError: If the configured orchestrator class cannot be found.
            TypeError: If the resolved class is not a subclass of BaseOrchestrator.
        """
        orchestrator_name = workflow.profile.orchestrator_class

        try:
            module = sys.modules[__name__]
            orchestrator_class = getattr(module, orchestrator_name)
        except AttributeError as exc:
            raise AttributeError(
                f"Orchestrator class '{orchestrator_name}' not found"
            ) from exc

        if not issubclass(orchestrator_class, BaseOrchestrator):
            raise TypeError(
                f"{orchestrator_name} is not a subclass of BaseOrchestrator"
            )

        return orchestrator_class(
            workflow=workflow,
            user=user,
            context=context,
        )


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
                yield mock_response[i:i+chunk_size].encode("utf-8")

        return stream_generator()


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


class SessionBasedOrchestrator(BaseOrchestrator):
    """Orchestrator that provides session-based LLM responses."""

    def __init__(self, workflow, user, context):
        from openedx_ai_extensions.workflows.models import AIWorkflowSession  # pylint: disable=import-outside-toplevel

        super().__init__(workflow, user, context)
        self.session, _ = AIWorkflowSession.objects.get_or_create(
            user=self.user,
            scope=self.workflow,
            profile=self.workflow.profile,
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
            self.profile.processor_config, self.session
        )

    def run(self, input_data):
        raise NotImplementedError("Subclasses must implement run method")


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

        # 2. Process with LLM processor
        llm_processor = EducatorAssistantProcessor(
            config=self.profile.processor_config,
            user=self.user,
            context=content_result
        )
        llm_result = llm_processor.process(input_data=input_data)

        if 'error' in llm_result:
            return {'error': llm_result['error'], 'status': 'LLMProcessor error'}

        lib_key_str = input_data.get('library_id')

        library_processor = ContentLibraryProcessor(
            library_key=lib_key_str,
            user=self.user,
            config=self.profile.processor_config
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

    def run_async(self, input_data):
        """
        Launch async task to execute the run method.

        Args:
            input_data: Input data to pass to the run method
        """

        self.session.course_id = self.course_id
        self.session.location_id = self.location_id
        self.session.save()

        task = _execute_orchestrator_async.delay(
            session_id=self.session.id,
            action='run',
            params={
                "input_data": input_data,
            }
        )

        return {
            'status': 'processing',
            'task_id': task.id,
            'message': 'AI workflow has started'
        }

    def get_run_status(self, input_data):  # pylint: disable=unused-argument
        """
        Get the status of an async task from session metadata.

        Returns:
            dict: Status information including task result if completed
        """
        metadata = self.session.metadata or {}
        task_status = metadata.get('task_status', 'processing')

        if task_status == 'completed':
            return metadata.get('task_result', {
                'status': 'completed',
                'message': 'Task completed but no result found'
            })
        elif task_status == 'error':
            return {
                'status': 'error',
                'error': metadata.get('task_error', 'Unknown error occurred')
            }
        elif task_status == 'timeout':
            return {
                'status': 'timeout',
                'error': metadata.get('task_error', 'Task exceeded time limit')
            }
        else:
            return {
                'status': 'processing',
                'message': 'AI workflow is running'
            }


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
