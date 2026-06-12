"""
Fixtures and helpers for live LLM provider integration tests.

Fixtures here are auto-loaded by pytest for all tests under tests/integration/.
"""

import json
import os
import sys
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator
from rest_framework.test import APIClient

for _mod in ("xmodule", "xmodule.modulestore", "xmodule.modulestore.django"):
    sys.modules.setdefault(_mod, MagicMock())

import settings as _settings  # noqa: E402  pylint: disable=wrong-import-position

_settings.SERVICE_VARIANT = "lms"


from openedx_ai_extensions.workflows.models import (  # noqa: E402  pylint: disable=wrong-import-position
    AIWorkflowProfile,
    AIWorkflowScope,
    AIWorkflowSession,
)

User = get_user_model()

PROVIDERS = [
    pytest.param("test_openai", "OPENAI_API_KEY", id="openai"),
    pytest.param("test_anthropic", "ANTHROPIC_API_KEY", id="anthropic"),
]

INVALID_CREDENTIALS = {
    "test_openai": {
        "bad_key": "sk-invalid-key-00000000000000000000000000000000",
        "bad_model": "openai/gpt-nonexistent-model-2099",
    },
    "test_anthropic": {
        "bad_key": (
            "sk-ant-api03-invalid000000000000000000000000000000000000000000000000000000000000000000000000000AA"
        ),
        "bad_model": "anthropic/claude-nonexistent-model-2099",
    },
}

LIVE_USER_USERNAME = "live_tester"
LIVE_USER_EMAIL = "live_tester@example.com"
LIVE_USER_PASSWORD = "livetest123"


def skip_if_no_key(env_var: str) -> None:
    """Skip the calling test at runtime if *env_var* is not set."""
    if not os.environ.get(env_var):
        pytest.skip(f"{env_var} not set — skipping live LLM test")


def create_profile_and_scope(  # pylint: disable=redefined-outer-name
    provider_slug: str,
    course_key,
    base_filepath: str,
    *,
    slug_suffix: str = "",
    extra_llm_patch: dict | None = None,
) -> AIWorkflowProfile:
    """
    Create an AIWorkflowProfile + AIWorkflowScope that routes LLM calls to
    *provider_slug* (a key in settings.AI_EXTENSIONS).

    The scope matches any location_id containing "live_unit" inside *course_key*.
    """
    llm_patch: dict = {"provider": provider_slug, "stream": False}
    if extra_llm_patch:
        llm_patch.update(extra_llm_patch)

    patch = {"processor_config": {"LLMProcessor": llm_patch}}

    profile = AIWorkflowProfile.objects.create(
        slug=f"live-{provider_slug}-{slug_suffix}",
        description=f"Live integration test — {provider_slug} / {slug_suffix}",
        base_filepath=base_filepath,
        content_patch=json.dumps(patch),
    )
    AIWorkflowScope.objects.create(
        location_regex=r".*live_unit.*",
        course_id=course_key,
        service_variant="lms",
        profile=profile,
        enabled=True,
        ui_slot_selector_id="live-test-slot",
    )
    return profile


def create_live_session(user, course_key, *, remote_response_id=None) -> AIWorkflowSession:  # pylint: disable=W0621
    """
    Create a minimal AIWorkflowSession backed by real DB rows.

    Creates a throw-away AIWorkflowProfile + AIWorkflowScope so the session
    FK constraints are satisfied without depending on specific fixture data.
    """
    profile = AIWorkflowProfile.objects.create(
        slug=f"live-session-profile-{user.pk}",
        description="Throw-away profile for threading tests",
        base_filepath="base/summary.json",
        content_patch="{}",
    )
    scope = AIWorkflowScope.objects.create(
        location_regex=r".*live_unit.*",
        course_id=course_key,
        service_variant="lms",
        profile=profile,
        enabled=True,
        ui_slot_selector_id="live-test-slot",
    )
    return AIWorkflowSession.objects.create(
        user=user,
        scope=scope,
        profile=profile,
        course_id=course_key,
        remote_response_id=remote_response_id,
    )


@pytest.fixture
def course_key():
    return CourseKey.from_string("course-v1:edX+LiveTest+Demo_Course")


@pytest.fixture
def location_id(course_key):  # pylint: disable=redefined-outer-name
    return BlockUsageLocator(course_key, block_type="vertical", block_id="live_unit_001")


@pytest.fixture
def live_user(db):  # pylint: disable=unused-argument
    return User.objects.create_user(
        username=LIVE_USER_USERNAME,
        email=LIVE_USER_EMAIL,
        password=LIVE_USER_PASSWORD,
    )


@pytest.fixture
def live_api_client(live_user):  # pylint: disable=redefined-outer-name,unused-argument
    client = APIClient()
    client.login(username=LIVE_USER_USERNAME, password=LIVE_USER_PASSWORD)
    return client
