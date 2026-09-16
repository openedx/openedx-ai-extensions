"""
Tests for the ``ai_extensions`` XBlock runtime service PoC (ADR-0011).

The service is exercised exactly as the proposed XBlock runtime fallback
would: instantiated with ``runtime=`` and ``xblock=`` keyword arguments and
asked to run a profile. No Django or XBlock machinery is required.
"""

from unittest.mock import MagicMock, Mock

from openedx_ai_extensions.xblock_service import AIExtensionsService


def make_block(usage_key="block-v1:org+course+run+type@problem+block@1",
               context_key="course-v1:org+course+run",
               user_id=42):
    """Build a mock XBlock exposing the scope_ids attributes the service reads."""
    usage_id = MagicMock()
    usage_id.context_key = context_key
    usage_id.__str__.return_value = usage_key
    block = Mock()
    block.scope_ids.usage_id = usage_id
    block.scope_ids.user_id = user_id
    return block


def test_service_instantiates_with_runtime_contract():
    runtime = Mock()
    block = make_block()
    service = AIExtensionsService(runtime=runtime, xblock=block)
    assert service.runtime is runtime
    assert service.xblock is block


def test_run_profile_returns_stub_with_context():
    service = AIExtensionsService(runtime=Mock(), xblock=make_block())
    result = service.run_profile("summarize-v1", {"text": "hello"})

    assert result["status"] == "ok"
    assert result["stub"] is True
    assert result["profile_id"] == "summarize-v1"
    assert result["echo"] == {"text": "hello"}
    assert result["context"]["course_key"] == "course-v1:org+course+run"
    assert result["context"]["user_id"] == 42
    assert "block-v1:" in result["context"]["usage_key"]


def test_run_profile_survives_minimal_context():
    # Some runtimes/tests may hand in blocks without full scope_ids; the
    # service should degrade to None context values, not raise.
    service = AIExtensionsService()
    result = service.run_profile("p1", "input")
    assert result["status"] == "ok"
    assert result["context"] == {
        "usage_key": None,
        "course_key": None,
        "user_id": None,
    }


def test_entry_point_target_is_importable():
    # Guards the setup.py entry point target string.
    from openedx_ai_extensions.xblock_service import service as service_module
    assert service_module.AIExtensionsService is AIExtensionsService
