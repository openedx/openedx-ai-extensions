"""
openedx_ai_extensions Django application initialization.
"""

from django.apps import AppConfig
from edx_django_utils.plugins.constants import PluginSettings, PluginSignals, PluginURLs


class OpenedxAIExtensionsConfig(AppConfig):
    # pylint: disable=line-too-long
    """
    Configuration for the openedx_ai_extensions Django application.

    See https://github.com/openedx/edx-django-utils/blob/master/edx_django_utils/plugins/docs/how_tos/how_to_create_a_plugin_app.rst#manual-setup
    for more details and examples.
    """  # noqa:

    default_auto_field = "django.db.models.BigAutoField"
    name = "openedx_ai_extensions"
    plugin_app = {
        "url_config": {
            "lms.djangoapp": {
                PluginURLs.NAMESPACE: "openedx_ai_extensions",
                PluginURLs.REGEX: r"^openedx-ai-extensions/",
                PluginURLs.RELATIVE_PATH: "urls",
            },
            "cms.djangoapp": {
                PluginURLs.NAMESPACE: "openedx_ai_extensions",
                PluginURLs.REGEX: r"^openedx-ai-extensions/",
                PluginURLs.RELATIVE_PATH: "urls",
            },
        },
        PluginSettings.CONFIG: {
            "lms.djangoapp": {
                "common": {
                    PluginURLs.RELATIVE_PATH: "settings.common",
                },
                "test": {
                    PluginURLs.RELATIVE_PATH: "settings.test",
                },
                "production": {
                    PluginURLs.RELATIVE_PATH: "settings.production",
                },
            },
            "cms.djangoapp": {
                "common": {
                    PluginURLs.RELATIVE_PATH: "settings.common",
                },
                "test": {
                    PluginURLs.RELATIVE_PATH: "settings.test",
                },
                "production": {
                    PluginURLs.RELATIVE_PATH: "settings.production",
                },
            },
        },
        PluginSignals.CONFIG: {
            "lms.djangoapp": {
                PluginURLs.RELATIVE_PATH: "signals",
                PluginSignals.RECEIVERS: [
                    # Signals handlers can be registered here
                ],
            },
            "cms.djangoapp": {
                PluginURLs.RELATIVE_PATH: "signals",
                PluginSignals.RECEIVERS: [
                    # Signals handlers can be registered here
                ],
            },
        },
    }
