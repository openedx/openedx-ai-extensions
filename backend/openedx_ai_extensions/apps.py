"""
openedx_ai_extensions Django application initialization.
"""

import logging

from django.apps import AppConfig
from edx_django_utils.plugins.constants import PluginSettings, PluginSignals, PluginURLs

from openedx_ai_extensions import __version__

logger = logging.getLogger(__name__)


class OpenedxAIExtensionsConfig(AppConfig):
    # pylint: disable=line-too-long
    """
    Configuration for the openedx_ai_extensions Django application.

    See https://github.com/openedx/edx-django-utils/blob/master/edx_django_utils/plugins/docs/how_tos/how_to_create_a_plugin_app.rst#manual-setup
    for more details and examples.
    """  # noqa:

    default_auto_field = "django.db.models.BigAutoField"
    name = "openedx_ai_extensions"
    verbose_name = f"Open edX AI Extensions (v{__version__})"

    def ready(self):
        """
        Import xAPI transformers to register them with the XApiTransformersRegistry.

        This ensures that our custom event transformers are available when the
        event-routing-backends processor looks them up.
        """
        # Import the transformers module to trigger the @register decorators
        # Import the tasks module to trigger the registration
        from openedx_ai_extensions import tasks  # noqa: F401 pylint: disable=unused-import,import-outside-toplevel
        from openedx_ai_extensions.xapi import \
            transformers  # noqa: F401 pylint: disable=unused-import,import-outside-toplevel

        self._configure_llm_cache()

    def _configure_llm_cache(self):
        """
        Initialise the LiteLLM cache backend from ``AI_EXTENSIONS_LLM_CACHE``.

        The setting is a dict with at least ``{"enabled": True/False}``.
        Additional keys are forwarded verbatim to ``litellm.Cache(**kwargs)``.

        Example (Redis)::

            AI_EXTENSIONS_LLM_CACHE = {
                "enabled": True,
                "type": "redis",
                "host": "localhost",
                "port": 6379,
            }
        """
        try:
            import litellm  # pylint: disable=import-outside-toplevel
            from django.conf import settings  # pylint: disable=import-outside-toplevel

            cache_config = getattr(settings, "AI_EXTENSIONS_LLM_CACHE", {})
            if not isinstance(cache_config, dict) or not cache_config.get("enabled"):
                return

            cache_kwargs = {k: v for k, v in cache_config.items() if k != "enabled"}
            litellm.cache = litellm.Cache(**cache_kwargs)
            logger.info(
                "LiteLLM cache initialised (type=%s)",
                cache_kwargs.get("type", "default"),
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to initialise LiteLLM cache")

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
