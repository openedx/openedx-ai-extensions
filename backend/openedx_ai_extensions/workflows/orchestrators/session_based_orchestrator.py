"""
Session-based orchestrator.
"""
import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from openedx_ai_extensions.processors import SubmissionProcessor
from openedx_ai_extensions.workflows.models import AIWorkflowSession

from .base_orchestrator import BaseOrchestrator

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


class SessionBasedOrchestrator(BaseOrchestrator):
    """Orchestrator that provides session-based LLM responses."""

    def __init__(self, workflow, user, context):

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
