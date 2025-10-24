"""
Tests to verify the plugin is discoverable and loaded correctly.
"""

from django.apps import apps
from django.conf import settings


def test_app_is_installed():
    """
    Test that the plugin app is installed in Django.

    This confirms that the plugin entrypoints are correct and that the
    plugin tooling was able to correctly load the plugin and add the app to
    INSTALLED_APPS

    """
    assert (
        "openedx_ai_extensions.apps.OpenedxAIExtensionsConfig"
        in settings.INSTALLED_APPS
    )
    assert apps.get_app_config("openedx_ai_extensions") is not None


# We don't do a test for the URLs because the namespaced urls which should be auto registered are tested in the
# test_api.py tests.
