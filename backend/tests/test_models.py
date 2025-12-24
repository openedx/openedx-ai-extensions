#!/usr/bin/env python
"""
Tests for the `openedx-ai-extensions` models module.
"""

import time
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey

from openedx_ai_extensions.models import PromptTemplate

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
