"""
Tests to verify the plugin is discoverable and loaded correctly.
"""
from types import SimpleNamespace

from django.apps import apps
from django.conf import settings

import openedx_ai_extensions.settings.common as common_settings


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


# ---------------------------------------------------------------------------
# Event bus consumer settings (AI_EXTENSIONS_ENABLE_EVENT_BUS_CONSUMER)
# ---------------------------------------------------------------------------

EVENT_TYPE = "org.openedx.ai_extensions.orchestration.requested.v1"
TOPIC = "ai-orchestration-requests"


def _minimal_settings(**extra):
    """Return a minimal settings namespace accepted by plugin_settings."""
    ns = SimpleNamespace(
        EVENT_TRACKING_BACKENDS={},
        EVENT_TRACKING_BACKENDS_ALLOWED_XAPI_EVENTS=[],
        EVENT_TRACKING_BACKENDS_ALLOWED_CALIPER_EVENTS=[],
        **extra,
    )
    return ns


def test_event_bus_consumer_not_set_when_flag_absent():
    """EVENT_BUS_CONSUMER_CONFIG must not be touched when the flag is absent."""
    fake = _minimal_settings()
    common_settings.plugin_settings(fake)
    assert not hasattr(fake, "EVENT_BUS_CONSUMER_CONFIG")
    assert not hasattr(fake, "EVENT_BUS_CONSUMER")


def test_event_bus_consumer_not_set_when_flag_false():
    """EVENT_BUS_CONSUMER_CONFIG must not be touched when the flag is False."""
    fake = _minimal_settings(AI_EXTENSIONS_ENABLE_EVENT_BUS_CONSUMER=False)
    common_settings.plugin_settings(fake)
    assert not hasattr(fake, "EVENT_BUS_CONSUMER_CONFIG")
    assert not hasattr(fake, "EVENT_BUS_CONSUMER")


def test_event_bus_consumer_set_when_flag_true():
    """When the flag is True, consumer settings are injected."""
    fake = _minimal_settings(AI_EXTENSIONS_ENABLE_EVENT_BUS_CONSUMER=True)
    common_settings.plugin_settings(fake)

    assert fake.EVENT_BUS_CONSUMER == "edx_event_bus_redis.RedisEventConsumer"
    assert EVENT_TYPE in fake.EVENT_BUS_CONSUMER_CONFIG
    assert TOPIC in fake.EVENT_BUS_CONSUMER_CONFIG[EVENT_TYPE]
    topic_cfg = fake.EVENT_BUS_CONSUMER_CONFIG[EVENT_TYPE][TOPIC]
    assert topic_cfg["group_id"] == "ai-extensions-orchestrator"
    assert topic_cfg["enabled"] is True


def test_event_bus_consumer_does_not_overwrite_existing_consumer():
    """If EVENT_BUS_CONSUMER is already set, it must not be overwritten."""
    fake = _minimal_settings(
        AI_EXTENSIONS_ENABLE_EVENT_BUS_CONSUMER=True,
        EVENT_BUS_CONSUMER="my.custom.Consumer",
    )
    common_settings.plugin_settings(fake)
    assert fake.EVENT_BUS_CONSUMER == "my.custom.Consumer"


def test_event_bus_consumer_config_merges_with_existing():
    """Existing EVENT_BUS_CONSUMER_CONFIG keys must not be wiped out."""
    existing_config = {"org.openedx.other.event.v1": {"other-topic": {"enabled": True}}}
    fake = _minimal_settings(
        AI_EXTENSIONS_ENABLE_EVENT_BUS_CONSUMER=True,
        EVENT_BUS_CONSUMER_CONFIG=existing_config,
    )
    common_settings.plugin_settings(fake)

    # The pre-existing key must still be present
    assert "org.openedx.other.event.v1" in fake.EVENT_BUS_CONSUMER_CONFIG
    # And the new event type must also have been added
    assert EVENT_TYPE in fake.EVENT_BUS_CONSUMER_CONFIG
