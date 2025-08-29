#!/usr/bin/env python
# pylint: disable=redefined-outer-name
"""
Tests for the `openedx-ai-extensions` models module.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from opaque_keys.edx.keys import CourseKey

from openedx_ai_extensions.models import CourseArchiveStatus

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


@pytest.mark.django_db
def test_course_archive_status_creation(user, course_key):
    """
    Test that a CourseArchiveStatus can be created with valid data.
    """
    course_archive_status = CourseArchiveStatus.objects.create(
        course_id=course_key, user=user, is_archived=False
    )

    assert course_archive_status.pk is not None
    assert course_archive_status.course_id == course_key
    assert course_archive_status.user == user
    assert course_archive_status.is_archived is False
    assert course_archive_status.archive_date is None
    assert course_archive_status.created_at is not None
    assert course_archive_status.updated_at is not None


@pytest.mark.django_db
def test_course_archive_status_uniqueness(user, course_key):
    """
    Test that a CourseArchiveStatus must be unique per user and course_id.
    """
    CourseArchiveStatus.objects.create(
        course_id=course_key, user=user, is_archived=False
    )

    # Creating another with same user and course_id should raise an IntegrityError
    with pytest.raises(IntegrityError):
        CourseArchiveStatus.objects.create(
            course_id=course_key, user=user, is_archived=True
        )


@pytest.mark.django_db
def test_course_archive_status_str_method(user, course_key):
    """
    Test the string representation of CourseArchiveStatus.
    """
    course_archive_status = CourseArchiveStatus.objects.create(
        course_id=course_key, user=user, is_archived=True
    )

    expected_str = f"{course_key} - {user.username} - Archived"
    assert str(course_archive_status) == expected_str

    course_archive_status.is_archived = False
    course_archive_status.save()

    expected_str = f"{course_key} - {user.username} - Not Archived"
    assert str(course_archive_status) == expected_str
