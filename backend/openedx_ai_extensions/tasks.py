"""
Celery tasks that will be registered.
"""
# pylint: disable=unused-import
from openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator import \
    _execute_orchestrator_async  # noqa: F401
