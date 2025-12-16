"""
Test the AI workflow xAPI transformers.

Uses the XApiTransformersFixturesTestMixin pattern from completion-aggregator
to test transformers using fixtures instead of manual assertions.
"""
import os
from unittest.mock import patch
from uuid import UUID

import ddt
from django.conf import settings
from django.test import TestCase
from event_routing_backends.processors.xapi.tests.test_transformers import XApiTransformersFixturesTestMixin
from event_routing_backends.settings import common as erb_settings

from openedx_ai_extensions.settings import common as common_settings
from openedx_ai_extensions.xapi import \
    transformers  # noqa: F401 - Import to register transformers  # pylint: disable=unused-import


@ddt.ddt
class TestXApiTransformers(XApiTransformersFixturesTestMixin, TestCase):
    """
    Test xAPI event transforms for AI workflows.

    This test class uses the XApiTransformersFixturesTestMixin to automatically
    discover and test all event fixtures in the fixtures/raw/ directory.

    How it works:
    1. Create a raw event JSON file in fixtures/raw/ (what tracker.emit() sends)
    2. Create expected xAPI statement in fixtures/expected/ (what should be generated)
    3. The mixin automatically tests the transformation
    """
    TEST_DIR_PATH = os.path.dirname(os.path.abspath(__file__))

    EVENT_FIXTURE_FILENAMES = [
        event_file_name for event_file_name in os.listdir(
            f'{TEST_DIR_PATH}/fixtures/raw/'
        ) if event_file_name.endswith(".json")
    ]

    @property
    def raw_events_fixture_path(self):
        """
        Return the path to the raw events fixture files.
        """
        return f'{self.TEST_DIR_PATH}/fixtures/raw'

    @property
    def expected_events_fixture_path(self):
        """
        Return the path to the expected transformed events fixture files.
        """
        return f'{self.TEST_DIR_PATH}/fixtures/expected'

    def setUp(self):
        """
        Initialize the plugin settings to register transformers.
        """
        erb_settings.plugin_settings(settings)
        common_settings.plugin_settings(settings)

        super().setUp()

    @patch('event_routing_backends.processors.xapi.transformer.get_anonymous_user_id')
    @patch('event_routing_backends.processors.xapi.transformer.get_course_from_id')
    @ddt.data(*EVENT_FIXTURE_FILENAMES)
    def test_event_transformer(self, raw_event_file_path, mock_get_course_from_id, mock_get_anonymous_user_id):
        """
        Test that raw events are transformed into correct xAPI statements.

        This test:
        1. Loads a raw event from fixtures/raw/
        2. Transforms it using our registered transformers
        3. Compares the result to the expected statement in fixtures/expected/
        """
        # Mock the anonymous user ID for consistent test results
        mock_get_anonymous_user_id.return_value = UUID('32e08e30-f8ae-4ce2-94a8-c2bfe38a70cb')

        # Mock the course data for contextActivities
        mock_get_course_from_id.return_value = {
            "display_name": "Demonstration Course",
            "id": "course-v1:edX+DemoX+Demo_Course",
        }

        # Only test events that have expected fixtures
        base_event_filename = os.path.basename(raw_event_file_path)
        expected_event_file_path = f'{self.expected_events_fixture_path}/{base_event_filename}'

        assert os.path.isfile(expected_event_file_path), \
            f"Missing expected fixture for {base_event_filename}"

        # The magic happens here - check_event_transformer does all the work!
        self.check_event_transformer(raw_event_file_path, expected_event_file_path)
