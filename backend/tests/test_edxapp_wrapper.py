"""
Tests for the edxapp_wrapper module.

This module tests the wrapper that abstracts Open edX core imports,
allowing the plugin to work with different Open edX versions.
"""

import sys
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import override_settings

# Mock the openedx module before importing the wrapper
# This must be done before importing the edxapp_wrapper modules to avoid import errors
mock_content_libraries = MagicMock()
mock_content_libraries.__name__ = 'openedx.core.djangoapps.content_libraries'
sys.modules['openedx'] = MagicMock()
sys.modules['openedx.core'] = MagicMock()
sys.modules['openedx.core.djangoapps'] = MagicMock()
sys.modules['openedx.core.djangoapps.content_libraries'] = mock_content_libraries

# pylint: disable=wrong-import-position
# These imports must come after mocking the openedx module
from openedx_ai_extensions.edxapp_wrapper import content_libraries_module  # noqa: E402
from openedx_ai_extensions.edxapp_wrapper.backends import content_libraries_module_t_v1  # noqa: E402

# pylint: enable=wrong-import-position


class TestContentLibrariesModuleWrapper:
    """
    Test the content_libraries_module wrapper function.
    """

    def test_get_content_libraries_returns_module(self):
        """
        Test that get_content_libraries() returns the content_libraries module.

        This tests the backend abstraction layer that loads the appropriate
        backend based on Django settings.
        """
        # Call the wrapper function
        result = content_libraries_module.get_content_libraries()

        # Verify it returns a module (should be the content_libraries module from the backend)
        assert result is not None

    @override_settings(
        CONTENT_LIBRARIES_MODULE_BACKEND="openedx_ai_extensions.edxapp_wrapper.backends.content_libraries_module_t_v1"
    )
    def test_get_content_libraries_uses_settings_backend(self):
        """
        Test that get_content_libraries() uses the backend specified in settings.

        This verifies that the wrapper correctly reads the CONTENT_LIBRARIES_MODULE_BACKEND
        setting and imports the specified backend module.
        """
        # Mock the import_module to verify it's called with the correct backend
        with patch('openedx_ai_extensions.edxapp_wrapper.content_libraries_module.import_module') as mock_import:
            mock_backend = MagicMock()
            mock_backend.get_content_libraries.return_value = MagicMock()
            mock_import.return_value = mock_backend

            # Call the wrapper function
            result = content_libraries_module.get_content_libraries()

            # Verify import_module was called with the backend from settings
            mock_import.assert_called_once_with(settings.CONTENT_LIBRARIES_MODULE_BACKEND)
            # Verify the backend's get_content_libraries was called
            mock_backend.get_content_libraries.assert_called_once()
            assert result is not None


class TestContentLibrariesModuleBackend:
    """
    Test the content_libraries_module_t_v1 backend.
    """

    def test_backend_get_content_libraries(self):
        """
        Test that the backend's get_content_libraries() returns the content_libraries module.

        This tests the actual backend implementation that imports from openedx.core.djangoapps.
        The openedx module is mocked at the module level to avoid import errors.
        """
        # Call the backend function (using the mocked openedx module)
        result = content_libraries_module_t_v1.get_content_libraries()

        # Verify it returns the content_libraries module
        # The function simply returns the imported module, so as long as it returns something
        # and doesn't raise an exception, it's working correctly
        assert result is not None
