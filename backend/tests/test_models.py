#!/usr/bin/env python
"""
Tests for the `openedx-ai-extensions` models module.
"""

import time
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator

from openedx_ai_extensions.models import PromptTemplate
from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope, AIWorkflowSession

User = get_user_model()


@pytest.fixture
def user():
    """
    Create and return a test user.
    """
    return User.objects.create_user(
        username="testuser", email="testuser@example.com", password="password123"
    )


@pytest.fixture
def staff_user():
    """
    Create and return a test staff user.
    """
    return User.objects.create_user(
        username="staffuser",
        email="staffuser@example.com",
        password="password123",
        is_staff=True,
    )


@pytest.fixture
def course_key():
    """
    Create and return a test course key.
    """
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.fixture
def prompt_template():
    """
    Create and return a test prompt template.
    """
    return PromptTemplate.objects.create(
        slug="test-prompt",
        body="You are a helpful AI assistant. Please help with: {context}"
    )


@pytest.mark.django_db
class TestPromptTemplate:
    """Tests for PromptTemplate model."""

    # pylint: disable=redefined-outer-name
    # Note: pytest fixtures intentionally "redefine" names from outer scope

    def test_create_prompt_template(self):
        """Test creating a PromptTemplate instance."""
        template = PromptTemplate.objects.create(
            slug="eli5",
            body="Explain this like I'm five years old: {content}"
        )
        assert template.slug == "eli5"
        assert template.body == "Explain this like I'm five years old: {content}"
        assert template.id is not None
        assert template.created_at is not None
        assert template.updated_at is not None

    def test_prompt_template_str(self, prompt_template):
        """Test __str__ method returns slug."""
        assert str(prompt_template) == "test-prompt"

    def test_prompt_template_repr(self, prompt_template):
        """Test __repr__ method."""
        assert repr(prompt_template) == "<PromptTemplate: test-prompt>"

    def test_load_prompt_by_slug(self, prompt_template):
        """Test loading prompt by slug."""
        result = PromptTemplate.load_prompt(prompt_template.slug)
        assert result == prompt_template.body

    def test_load_prompt_by_uuid(self, prompt_template):
        """Test loading prompt by UUID."""
        result = PromptTemplate.load_prompt(str(prompt_template.id))
        assert result == "You are a helpful AI assistant. Please help with: {context}"

    def test_load_prompt_by_uuid_without_dashes(self, prompt_template):
        """Test loading prompt by UUID without dashes."""
        uuid_str = str(prompt_template.id).replace('-', '')
        result = PromptTemplate.load_prompt(uuid_str)
        assert result == "You are a helpful AI assistant. Please help with: {context}"

    def test_load_prompt_nonexistent_slug(self):
        """Test loading prompt with nonexistent slug returns None."""
        result = PromptTemplate.load_prompt("nonexistent-slug")
        assert result is None

    def test_load_prompt_nonexistent_uuid(self):
        """Test loading prompt with nonexistent UUID returns None."""
        result = PromptTemplate.load_prompt("12345678-1234-1234-1234-123456789abc")
        assert result is None

    def test_load_prompt_empty_identifier(self):
        """Test loading prompt with empty identifier returns None."""
        assert PromptTemplate.load_prompt("") is None
        assert PromptTemplate.load_prompt(None) is None

    def test_load_prompt_invalid_identifier(self):
        """Test loading prompt with invalid identifier returns None."""
        result = PromptTemplate.load_prompt("not-a-real-slug-or-uuid-12345")
        assert result is None

    def test_prompt_template_ordering(self):
        """Test that prompt templates are ordered by slug."""
        PromptTemplate.objects.create(slug="zebra", body="Z prompt")
        PromptTemplate.objects.create(slug="alpha", body="A prompt")
        PromptTemplate.objects.create(slug="beta", body="B prompt")

        templates = list(PromptTemplate.objects.all())
        slugs = [t.slug for t in templates]
        assert slugs == sorted(slugs)

    def test_prompt_template_unique_slug(self, prompt_template):
        """Test that slug must be unique."""
        # prompt_template fixture creates a template with slug "test-prompt"
        # Try to create another with the same slug - should fail
        with pytest.raises(Exception):  # IntegrityError
            PromptTemplate.objects.create(
                slug=prompt_template.slug,
                body="Different body"
            )

    def test_load_prompt_uuid_database_error(self, prompt_template, monkeypatch):
        """Test loading prompt by UUID handles database errors gracefully."""

        # Mock objects.get to raise a database error
        mock_objects = Mock()
        mock_objects.get.side_effect = ValueError("Database connection error")
        monkeypatch.setattr(PromptTemplate, 'objects', mock_objects)

        # Should return None on error
        result = PromptTemplate.load_prompt(str(prompt_template.id))
        assert result is None

    def test_load_prompt_slug_database_error(self, monkeypatch):
        """Test loading prompt by slug handles database errors gracefully."""

        # Mock objects.get to raise a database error
        mock_objects = Mock()
        mock_objects.get.side_effect = RuntimeError("Database error")
        monkeypatch.setattr(PromptTemplate, 'objects', mock_objects)

        # Should return None on error
        result = PromptTemplate.load_prompt("some-slug")
        assert result is None

    def test_prompt_template_updated_at(self, prompt_template):
        """Test that updated_at changes when model is saved."""

        original_updated = prompt_template.updated_at

        # Wait a tiny bit and update
        time.sleep(0.01)
        prompt_template.body = "Updated body content"
        prompt_template.save()

        # Refresh from database
        prompt_template.refresh_from_db()
        assert prompt_template.updated_at > original_updated

    def test_prompt_template_case_sensitive_uuid(self, prompt_template):
        """Test that UUID matching is case-insensitive."""
        # Test with uppercase UUID
        uuid_upper = str(prompt_template.id).upper()
        result = PromptTemplate.load_prompt(uuid_upper)
        assert result == prompt_template.body

        # Test with mixed case
        uuid_mixed = str(prompt_template.id).replace('a', 'A').replace('b', 'B')
        result = PromptTemplate.load_prompt(uuid_mixed)
        assert result == prompt_template.body


# ============================================================================
# AIWorkflowSession Thread Tests
# ============================================================================


@pytest.fixture
def workflow_profile(db):  # pylint: disable=unused-argument
    """Create a test workflow profile."""
    return AIWorkflowProfile.objects.create(
        slug="test-thread-profile",
        base_filepath="base/default.json",
        content_patch='{}',
    )


@pytest.fixture
def workflow_scope(workflow_profile, course_key):  # pylint: disable=redefined-outer-name
    """Create a test workflow scope."""
    return AIWorkflowScope.objects.create(
        location_regex=".*",
        course_id=course_key,
        service_variant="lms",
        profile=workflow_profile,
        enabled=True,
    )


@pytest.fixture
def session_with_ids(user, course_key, workflow_scope, workflow_profile):  # pylint: disable=redefined-outer-name
    """Create a session with both local and remote IDs."""
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-1")
    return AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        course_id=course_key,
        location_id=location,
        local_submission_id="sub-123",
        remote_response_id="resp-456",
    )


@pytest.fixture
def session_no_ids(user, course_key, workflow_scope, workflow_profile):  # pylint: disable=redefined-outer-name
    """Create a session with no submission or response IDs."""
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-1")
    return AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        course_id=course_key,
        location_id=location,
    )


@pytest.mark.django_db
class TestAIWorkflowSessionThreads:
    """Tests for get_local_thread, get_remote_thread, get_combined_thread."""

    # pylint: disable=redefined-outer-name

    def test_get_local_thread_no_submission(self, session_no_ids):
        """Returns None when no local_submission_id."""
        assert session_no_ids.get_local_thread() is None

    @patch("openedx_ai_extensions.processors.openedx.submission_processor.SubmissionProcessor.get_full_thread")
    def test_get_local_thread_with_submission(self, mock_thread, session_with_ids):
        """Calls SubmissionProcessor.get_full_thread when submission exists."""
        mock_thread.return_value = [{"role": "user", "content": "Hi"}]
        result = session_with_ids.get_local_thread()
        assert result == [{"role": "user", "content": "Hi"}]
        mock_thread.assert_called_once()

    def test_get_remote_thread_no_response_id(self, session_no_ids):
        """Returns None when no remote_response_id."""
        assert session_no_ids.get_remote_thread() is None

    @patch("openedx_ai_extensions.processors.llm.llm_processor.LLMProcessor.fetch_remote_thread")
    def test_get_remote_thread_with_response_id(self, mock_fetch, session_with_ids):
        """Calls LLMProcessor.fetch_remote_thread when response ID exists."""
        mock_fetch.return_value = [{"id": "resp-456", "output": []}]
        result = session_with_ids.get_remote_thread()
        assert result == [{"id": "resp-456", "output": []}]
        mock_fetch.assert_called_once_with("resp-456")

    @patch.object(AIWorkflowSession, "get_remote_thread", return_value=None)
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_no_remote(  # pylint: disable=unused-argument
        self, mock_local, mock_remote, session_with_ids,
    ):
        """Returns local thread when remote is None."""
        local = [{"role": "user", "content": "Hello"}]
        mock_local.return_value = local
        result = session_with_ids.get_combined_thread()
        assert result == local

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread", return_value=None)
    def test_combined_thread_remote_only(  # pylint: disable=unused-argument
        self, mock_local, mock_remote, session_with_ids,
    ):
        """Handles remote thread with no local thread."""
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-01T00:00:00",
                "model": "gpt-4",
                "input": [{"role": "user", "content": "Hi", "type": "message"}],
                "output": [{"role": "assistant", "content": "Hello!"}],
            }
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 2
        roles = [m["role"] for m in result]
        assert "user" in roles
        assert "assistant" in roles

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_deduplication(self, mock_local, mock_remote, session_with_ids):
        """Messages appearing in both local and remote are deduplicated."""
        mock_local.return_value = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00", "submission_id": "sub-1"},
        ]
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-01T00:00:00",
                "model": "gpt-4",
                "input": [{"role": "user", "content": "Hello", "type": "message"}],
                "output": [],
            }
        ]
        result = session_with_ids.get_combined_thread()
        # Should be deduplicated: one message with source="both"
        assert len(result) == 1
        assert result[0]["source"] == "both"
        assert result[0]["submission_id"] == "sub-1"

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_local_only_messages(self, mock_local, mock_remote, session_with_ids):
        """Local-only messages are inserted at correct position."""
        mock_local.return_value = [
            {"role": "user", "content": "Local only msg", "timestamp": "2024-01-01T12:00:00"},
        ]
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-02T00:00:00",
                "model": "gpt-4",
                "input": [{"role": "user", "content": "Remote msg", "type": "message"}],
                "output": [],
            }
        ]
        result = session_with_ids.get_combined_thread()
        # Local-only should be inserted before the remote message (earlier timestamp)
        assert len(result) == 2
        assert result[0]["source"] == "local"
        assert result[1]["source"] == "remote"

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_error_response(self, mock_local, mock_remote, session_with_ids):
        """Error responses in remote thread are handled."""
        mock_local.return_value = None
        mock_remote.return_value = [
            {"id": "resp-1", "error": "API timeout"},
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 1
        assert result[0]["role"] == "error"
        assert "API timeout" in result[0]["content"]

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_skips_non_dict(self, mock_local, mock_remote, session_with_ids):
        """Non-dict items in remote thread are skipped."""
        mock_local.return_value = None
        mock_remote.return_value = ["not-a-dict", None, 42]
        result = session_with_ids.get_combined_thread()
        assert result == []


# ==========================================================================
# AIWorkflowScope Resolution (multi-scope per location)
# ==========================================================================


@pytest.mark.django_db
class TestAIWorkflowScopeResolution:
    """Tests for AIWorkflowScope.get_profile resolution logic."""

    # pylint: disable=redefined-outer-name

    @staticmethod
    def _create_profile(slug: str) -> AIWorkflowProfile:
        return AIWorkflowProfile.objects.create(
            slug=slug,
            base_filepath="base/default.json",
            content_patch="{}",
        )

    def test_multi_scope_selects_most_specific(self, course_key):
        location_id = f"block-v1:{course_key}+type@vertical+block@unit-1"

        profile_course_level = self._create_profile("multi-scope-course-level")
        profile_location_specific = self._create_profile("multi-scope-location-specific")

        # Course-level scope: no location_regex → specificity_index = 2 (course_id + ui_slot_selector_id)
        AIWorkflowScope.objects.create(
            location_regex=None,
            course_id=course_key,
            service_variant="lms",
            profile=profile_course_level,
            enabled=True,
            ui_slot_selector_id="slot-a",
        )
        # Location-specific scope: has location_regex → specificity_index = 3
        scope_specific = AIWorkflowScope.objects.create(
            location_regex=r"unit-1$",
            course_id=course_key,
            service_variant="lms",
            profile=profile_location_specific,
            enabled=True,
            ui_slot_selector_id="slot-a",
        )

        resolved = AIWorkflowScope.get_profile(course_key, location_id, ui_slot_selector_id="slot-a")
        assert resolved.id == scope_specific.id
        assert resolved.profile.slug == "multi-scope-location-specific"

    def test_multi_scope_tie_specificity_raises(self, course_key):
        location_id = f"block-v1:{course_key}+type@vertical+block@unit-1"

        profile1 = self._create_profile("multi-scope-tie-1")
        profile2 = self._create_profile("multi-scope-tie-2")

        # Both scopes have the same location_regex → both get specificity_index=3 → tie
        AIWorkflowScope.objects.create(
            location_regex=r"unit-1$",
            course_id=course_key,
            service_variant="lms",
            profile=profile1,
            enabled=True,
            ui_slot_selector_id="slot-a",
        )
        AIWorkflowScope.objects.create(
            location_regex=r"unit-1$",
            course_id=course_key,
            service_variant="lms",
            profile=profile2,
            enabled=True,
            ui_slot_selector_id="slot-a",
        )

        with pytest.raises(ValueError, match=r"tie.*equal specificity_index"):
            AIWorkflowScope.get_profile(course_key, location_id, ui_slot_selector_id="slot-a")

    def test_legacy_prefers_legacy_scope_when_present(self, course_key):
        location_id = f"block-v1:{course_key}+type@vertical+block@unit-legacy"

        profile_legacy = self._create_profile("legacy-profile")
        profile_slot = self._create_profile("slot-profile")

        legacy_scope = AIWorkflowScope.objects.create(
            location_regex=r"unit-legacy$",
            course_id=course_key,
            service_variant="lms",
            profile=profile_legacy,
            enabled=True,
            ui_slot_selector_id=None,
        )
        AIWorkflowScope.objects.create(
            location_regex=r"unit-legacy$",
            course_id=course_key,
            service_variant="lms",
            profile=profile_slot,
            enabled=True,
            ui_slot_selector_id="slot-a",
        )

        resolved = AIWorkflowScope.get_profile(course_key, location_id)
        assert resolved.id == legacy_scope.id
        assert resolved.profile.slug == "legacy-profile"

    def test_legacy_falls_back_to_single_slot_match(self, course_key):
        location_id = f"block-v1:{course_key}+type@vertical+block@unit-fallback"

        profile_slot = self._create_profile("single-slot-fallback")

        scope = AIWorkflowScope.objects.create(
            location_regex=r"unit-fallback$",
            course_id=course_key,
            service_variant="lms",
            profile=profile_slot,
            enabled=True,
            ui_slot_selector_id="slot-a",
        )

        resolved = AIWorkflowScope.get_profile(course_key, location_id)
        assert resolved.id == scope.id

    def test_legacy_multiple_slot_matches_without_selector_raises(self, course_key):
        location_id = f"block-v1:{course_key}+type@vertical+block@unit-ambiguous"

        profile1 = self._create_profile("ambiguous-slot-1")
        profile2 = self._create_profile("ambiguous-slot-2")

        AIWorkflowScope.objects.create(
            location_regex=r"unit-ambiguous$",
            course_id=course_key,
            service_variant="lms",
            profile=profile1,
            enabled=True,
            ui_slot_selector_id="slot-a",
        )
        AIWorkflowScope.objects.create(
            location_regex=r"unit-ambiguous$",
            course_id=course_key,
            service_variant="lms",
            profile=profile2,
            enabled=True,
            ui_slot_selector_id="slot-b",
        )

        with pytest.raises(ValueError, match=r"no uiSlotSelectorId"):
            AIWorkflowScope.get_profile(course_key, location_id)

    # --- Non-string content from the API ---

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_local_content_as_list(self, mock_local, mock_remote, session_with_ids):
        """Local message with list content (multimodal) does not crash when a remote thread is present."""
        # The fix (content_str = ... if isinstance ...) lives in the local-thread
        # indexing loop, which only runs when remote_thread is truthy.
        mock_local.return_value = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello from a list"}],
                "timestamp": "2024-01-01T00:00:00",
                "submission_id": "sub-1",
            }
        ]
        mock_remote.return_value = [
            {"id": "resp-1", "created_at": "2024-01-02T00:00:00", "model": "gpt-4", "input": [], "output": []}
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 1
        assert result[0]["source"] == "local"
        assert result[0]["content"] == [{"type": "text", "text": "Hello from a list"}]

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_local_content_as_none(self, mock_local, mock_remote, session_with_ids):
        """Local message with explicit None content does not crash."""
        mock_local.return_value = [
            {"role": "user", "content": None, "timestamp": "2024-01-01T00:00:00", "submission_id": "sub-1"}
        ]
        mock_remote.return_value = [
            {"id": "resp-1", "created_at": "2024-01-02T00:00:00", "model": "gpt-4", "input": [], "output": []}
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 1
        assert result[0]["source"] == "local"

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread", return_value=None)
    def test_combined_thread_remote_input_content_as_list(  # pylint: disable=unused-argument
        self, mock_local, mock_remote, session_with_ids,
    ):
        """Remote input item with list content (multimodal API response) does not crash."""
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-01T00:00:00",
                "model": "gpt-4",
                "input": [
                    {
                        "role": "user",
                        "type": "message",
                        "content": [{"type": "text", "text": "Hello"}],
                    }
                ],
                "output": [],
            }
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread", return_value=None)
    def test_combined_thread_remote_output_content_as_list(  # pylint: disable=unused-argument
        self, mock_local, mock_remote, session_with_ids,
    ):
        """Remote output item with list content (multimodal API response) does not crash."""
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-01T00:00:00",
                "model": "gpt-4",
                "input": [],
                "output": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Hello back"}],
                    }
                ],
            }
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 1
        assert result[0]["role"] == "assistant"

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread")
    def test_combined_thread_dedup_with_list_content(self, mock_local, mock_remote, session_with_ids):
        """Deduplication works when both local and remote carry the same list content."""
        content_blocks = [{"type": "text", "text": "Hello"}]
        mock_local.return_value = [
            {
                "role": "user",
                "content": content_blocks,
                "timestamp": "2024-01-01T00:00:00",
                "submission_id": "sub-1",
            }
        ]
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-01T00:00:00",
                "model": "gpt-4",
                "input": [{"role": "user", "type": "message", "content": content_blocks}],
                "output": [],
            }
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 1
        assert result[0]["source"] == "both"
        assert result[0]["submission_id"] == "sub-1"

    # --- type field and tool-call field propagation ---

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread", return_value=None)
    def test_combined_thread_output_type_is_preserved(  # pylint: disable=unused-argument
        self, mock_local, mock_remote, session_with_ids,
    ):
        """Output items carry the real 'type' from the extracted item, not a hardcoded 'message'."""
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-01T00:00:00",
                "model": "gpt-4",
                "input": [],
                "output": [
                    {"type": "message", "role": "assistant", "content": "Hello!"},
                    {
                        "type": "function_call",
                        "role": "tool_call",
                        "name": "get_weather",
                        "arguments": '{"location": "Paris"}',
                        "call_id": "call_xyz",
                        "content": "get_weather({\"location\": \"Paris\"})",
                    },
                    {"type": "reasoning", "role": "reasoning", "content": "Thinking about weather."},
                ],
            }
        ]
        result = session_with_ids.get_combined_thread()
        types = {msg["type"] for msg in result}
        assert "message" in types
        assert "function_call" in types
        assert "reasoning" in types

    @patch.object(AIWorkflowSession, "get_remote_thread")
    @patch.object(AIWorkflowSession, "get_local_thread", return_value=None)
    def test_combined_thread_function_call_fields_propagated(  # pylint: disable=unused-argument
        self, mock_local, mock_remote, session_with_ids,
    ):
        """Function call output items expose name, arguments, and call_id in the combined thread."""
        mock_remote.return_value = [
            {
                "id": "resp-1",
                "created_at": "2024-01-01T00:00:00",
                "model": "gpt-4",
                "input": [],
                "output": [
                    {
                        "type": "function_call",
                        "role": "tool_call",
                        "name": "get_weather",
                        "arguments": '{"location": "Paris"}',
                        "call_id": "call_xyz789",
                        "content": "get_weather({\"location\": \"Paris\"})",
                    }
                ],
            }
        ]
        result = session_with_ids.get_combined_thread()
        assert len(result) == 1
        item = result[0]
        assert item["type"] == "function_call"
        assert item["name"] == "get_weather"
        assert item["arguments"] == '{"location": "Paris"}'
        assert item["call_id"] == "call_xyz789"
        # content is still present as a human-readable fallback
        assert "get_weather" in item["content"]
