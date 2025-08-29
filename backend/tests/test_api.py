#!/usr/bin/env python
# pylint: disable=redefined-outer-name
"""
Tests for the `openedx-ai-extensions` REST API.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from rest_framework import status
from rest_framework.test import APIClient

from openedx_ai_extensions.models import CourseArchiveStatus

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Return a REST framework API client.
    """
    return APIClient()


@pytest.fixture
def user():
    """
    Create and return a test user.
    """
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="password123",
    )


@pytest.fixture
def another_user():
    """
    Create and return another test user.
    """
    return User.objects.create_user(
        username="anotheruser",
        email="anotheruser@example.com",
        password="password123",
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
def course_archive_status(user, course_key):
    """
    Create and return a test course archive status.
    """
    return CourseArchiveStatus.objects.create(
        course_id=course_key, user=user, is_archived=False
    )


@pytest.mark.django_db
def test_list_course_archive_status_authenticated(
    api_client, user, course_archive_status
):
    """
    Test that an authenticated user can list their own course archive statuses.
    """
    api_client.force_authenticate(user=user)
    url = reverse("openedx_ai_extensions:course-archive-status-list")
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["course_id"] == str(
        course_archive_status.course_id
    )
    assert response.data["results"][0]["user"] == user.id
    assert (
        response.data["results"][0]["is_archived"] == course_archive_status.is_archived
    )


@pytest.mark.django_db
def test_list_course_archive_status_unauthenticated(api_client):
    """
    Test that an unauthenticated user cannot list course archive statuses.
    """
    url = reverse("openedx_ai_extensions:course-archive-status-list")
    response = api_client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_course_archive_status_staff_can_see_all(
    api_client, staff_user, user, another_user, course_key
):
    """
    Test that a staff user can list all course archive statuses.
    """
    # Create archive statuses for both users
    CourseArchiveStatus.objects.create(
        course_id=course_key, user=user, is_archived=False
    )
    CourseArchiveStatus.objects.create(
        course_id=CourseKey.from_string("course-v1:edX+DemoX+Demo_Course2"),
        user=another_user,
        is_archived=True,
    )

    api_client.force_authenticate(user=staff_user)
    url = reverse("openedx_ai_extensions:course-archive-status-list")
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_create_course_archive_status(api_client, user, course_key):
    """
    Test that a user can create a course archive status.
    """
    api_client.force_authenticate(user=user)
    url = reverse("openedx_ai_extensions:course-archive-status-list")
    data = {
        "course_id": str(course_key),
        "user": user.id,
        "is_archived": True,
    }
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["course_id"] == str(course_key)
    assert response.data["user"] == user.id
    assert response.data["is_archived"] is True
    assert response.data["archive_date"] is not None

    # Verify in database
    course_archive_status = CourseArchiveStatus.objects.get(
        course_id=course_key, user=user
    )
    assert course_archive_status.is_archived is True
    assert course_archive_status.archive_date is not None


@pytest.mark.django_db
def test_create_course_archive_status_for_another_user(
    api_client, user, another_user, course_key
):
    """
    Test that a regular user cannot create a course archive status for another user.
    """
    api_client.force_authenticate(user=user)
    url = reverse("openedx_ai_extensions:course-archive-status-list")
    data = {
        "course_id": str(course_key),
        "user": another_user.id,
        "is_archived": True,
    }
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_staff_create_course_archive_status_for_another_user(
    api_client, staff_user, user, course_key
):
    """
    Test that a staff user can create a course archive status for another user.
    """
    api_client.force_authenticate(user=staff_user)
    url = reverse("openedx_ai_extensions:course-archive-status-list")
    data = {
        "course_id": str(course_key),
        "user": user.id,
        "is_archived": True,
    }
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["course_id"] == str(course_key)
    assert response.data["user"] == user.id
    assert response.data["is_archived"] is True
    assert response.data["archive_date"] is not None


@pytest.mark.django_db
def test_update_course_archive_status(api_client, user, course_archive_status):
    """
    Test that a user can update their own course archive status.
    """
    api_client.force_authenticate(user=user)
    url = reverse(
        "openedx_ai_extensions:course-archive-status-detail", args=[course_archive_status.id]
    )
    data = {"is_archived": True}
    response = api_client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_archived"] is True
    assert response.data["archive_date"] is not None

    # Verify in database
    course_archive_status.refresh_from_db()
    assert course_archive_status.is_archived is True
    assert course_archive_status.archive_date is not None


@pytest.mark.django_db
def test_delete_course_archive_status(api_client, user, course_archive_status):
    """
    Test that a user can delete their own course archive status.
    """
    api_client.force_authenticate(user=user)
    url = reverse(
        "openedx_ai_extensions:course-archive-status-detail", args=[course_archive_status.id]
    )
    response = api_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert CourseArchiveStatus.objects.filter(id=course_archive_status.id).count() == 0


@pytest.mark.django_db
def test_cannot_update_other_user_course_archive_status(
    api_client, another_user, course_archive_status
):
    """
    Test that a user cannot update another user's course archive status.
    """
    api_client.force_authenticate(user=another_user)
    url = reverse(
        "openedx_ai_extensions:course-archive-status-detail", args=[course_archive_status.id]
    )
    data = {"is_archived": True}
    response = api_client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_staff_can_update_other_user_course_archive_status(
    api_client, staff_user, course_archive_status
):
    """
    Test that a staff user can update another user's course archive status.
    """
    api_client.force_authenticate(user=staff_user)
    url = reverse(
        "openedx_ai_extensions:course-archive-status-detail", args=[course_archive_status.id]
    )
    data = {"is_archived": True}
    response = api_client.patch(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_archived"] is True
