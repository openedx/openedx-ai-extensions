"""
Tests for the LitellmProcessor base class.
"""

from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from openedx_ai_extensions.functions.decorators import TOOLS_SCHEMA
from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

User = get_user_model()


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    """
    Create and return a test user.
    """
    return User.objects.create_user(
        username="testuser", email="testuser@example.com", password="password123"
    )


@pytest.fixture
def mock_ai_extensions_settings():
    """
    Mock AI_EXTENSIONS settings.
    """
    return {
        "default": {
            "MODEL": "openai/gpt-4",
            "API_KEY": "test-api-key",
            "TEMPERATURE": 0.7,
            "MAX_TOKENS": 2000,
        },
        "custom": {
            "MODEL": "anthropic/claude-3",
            "API_KEY": "test-custom-key",
        }
    }


@pytest.fixture
def basic_config():
    """
    Basic configuration for LitellmProcessor.
    """
    return {
        "LitellmProcessor": {
            "some_setting": "value",
        }
    }


# ============================================================================
# LitellmProcessor Initialization Tests
# ============================================================================


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
        "API_KEY": "test-api-key",
    }
})
@pytest.mark.django_db
def test_litellm_processor_initialization_basic(user):  # pylint: disable=redefined-outer-name,unused-argument
    """
    Test LitellmProcessor initialization with basic config.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert processor.config == {"config": "default"}
    assert processor.config_profile == "default"
    assert processor.provider == "openai"
    assert "model" in processor.extra_params
    assert processor.extra_params["model"] == "openai/gpt-4"
    assert processor.extra_params["api_key"] == "test-api-key"


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_litellm_processor_initialization_no_config(mock_settings):  # pylint: disable=unused-argument
    """
    Test LitellmProcessor initialization with no config provided.
    """
    processor = LitellmProcessor(config=None, user_session=None)

    assert processor.config == {}
    assert processor.config_profile == "default"
    assert processor.provider == "openai"


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {})
@pytest.mark.django_db
def test_litellm_processor_missing_config_profile_raises_error(mock_settings):  # pylint: disable=unused-argument
    """
    Test that missing config profile raises KeyError.
    """
    with pytest.raises(KeyError):
        LitellmProcessor(config=None, user_session=None)


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {}
})
@pytest.mark.django_db
def test_litellm_processor_missing_model_raises_error(mock_settings):  # pylint: disable=unused-argument
    """
    Test that missing MODEL key raises ValueError.
    """
    with pytest.raises(ValueError, match="missing 'MODEL' setting"):
        LitellmProcessor(config=None, user_session=None)


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": None,
    }
})
@pytest.mark.django_db
def test_litellm_processor_invalid_model_format_raises_error(mock_settings):  # pylint: disable=unused-argument
    """
    Test that invalid MODEL format (None) raises ValueError.
    """
    with pytest.raises(ValueError, match="must be in the format 'provider/model_name'"):
        LitellmProcessor(config=None, user_session=None)


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "custom": {
        "MODEL": "anthropic/claude-3",
        "API_KEY": "custom-key",
    }
})
@pytest.mark.django_db
def test_litellm_processor_custom_config_profile(mock_settings):  # pylint: disable=unused-argument
    """
    Test LitellmProcessor with custom config profile.
    """
    config = {
        "LitellmProcessor": {
            "config": "custom",
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert processor.config_profile == "custom"
    assert processor.provider == "anthropic"
    assert processor.extra_params["model"] == "anthropic/claude-3"
    assert processor.extra_params["api_key"] == "custom-key"


# ============================================================================
# Tools Configuration Tests
# ============================================================================


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_enabled_tools_empty_list(mock_settings):  # pylint: disable=unused-argument
    """
    Test that empty enabled_tools list does not add tools to extra_params.
    """
    config = {
        "LitellmProcessor": {
            "enabled_tools": [],
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert "tools" not in processor.extra_params


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_enabled_tools_not_provided(mock_settings):  # pylint: disable=unused-argument
    """
    Test that when enabled_tools is not provided, tools are not added.
    """
    config = {
        "LitellmProcessor": {}
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert "tools" not in processor.extra_params


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_enabled_tools_single_function(mock_settings):  # pylint: disable=unused-argument
    """
    Test that a single function in enabled_tools is properly configured.
    """
    config = {
        "LitellmProcessor": {
            "enabled_tools": ["roll_dice"],
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert "tools" in processor.extra_params
    assert len(processor.extra_params["tools"]) == 1
    assert processor.extra_params["tools"][0]["type"] == "function"
    assert "function" in processor.extra_params["tools"][0]
    assert processor.extra_params["tools"][0]["function"] == TOOLS_SCHEMA["roll_dice"]


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_enabled_tools_multiple_functions(mock_settings):  # pylint: disable=unused-argument
    """
    Test that multiple functions in enabled_tools are properly configured.
    """
    config = {
        "LitellmProcessor": {
            "enabled_tools": ["roll_dice", "get_location_content"],
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert "tools" in processor.extra_params
    assert len(processor.extra_params["tools"]) == 2

    # Verify structure of each tool
    for tool in processor.extra_params["tools"]:
        assert tool["type"] == "function"
        assert "function" in tool
        assert tool["function"] in TOOLS_SCHEMA.values()


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_enabled_tools_filters_only_enabled_functions(mock_settings):  # pylint: disable=unused-argument
    """
    Test that only functions listed in enabled_tools are included.
    """
    config = {
        "LitellmProcessor": {
            "enabled_tools": ["roll_dice"],
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    # Only roll_dice should be in tools
    assert len(processor.extra_params["tools"]) == 1
    assert processor.extra_params["tools"][0]["function"] == TOOLS_SCHEMA["roll_dice"]

    # get_location_content should not be in tools
    for tool in processor.extra_params["tools"]:
        assert tool["function"] != TOOLS_SCHEMA["get_location_content"]


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_enabled_tools_nonexistent_function(mock_settings):  # pylint: disable=unused-argument
    """
    Test that nonexistent functions in enabled_tools are silently ignored.
    """
    config = {
        "LitellmProcessor": {
            "enabled_tools": ["roll_dice", "nonexistent_function"],
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    # Only roll_dice should be in tools (nonexistent_function ignored)
    assert "tools" in processor.extra_params
    assert len(processor.extra_params["tools"]) == 1
    assert processor.extra_params["tools"][0]["function"] == TOOLS_SCHEMA["roll_dice"]


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_enabled_tools_all_available_functions(mock_settings):  # pylint: disable=unused-argument
    """
    Test that all available functions can be enabled.
    """
    all_function_names = list(TOOLS_SCHEMA.keys())
    config = {
        "LitellmProcessor": {
            "enabled_tools": all_function_names,
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert "tools" in processor.extra_params
    assert len(processor.extra_params["tools"]) == len(TOOLS_SCHEMA)

    # Verify all functions are included
    included_schemas = [tool["function"] for tool in processor.extra_params["tools"]]
    for schema in TOOLS_SCHEMA.values():
        assert schema in included_schemas


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_tools_schema_structure(mock_settings):  # pylint: disable=unused-argument
    """
    Test that the tools schema has the correct structure for LiteLLM.
    """
    config = {
        "LitellmProcessor": {
            "enabled_tools": ["roll_dice"],
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    tool = processor.extra_params["tools"][0]

    # Verify OpenAI-compatible tool structure
    assert isinstance(tool, dict)
    assert "type" in tool
    assert tool["type"] == "function"
    assert "function" in tool
    assert isinstance(tool["function"], dict)


# ============================================================================
# Extra Parameters Tests
# ============================================================================


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
        "API_KEY": "test-key",
        "TEMPERATURE": 0.5,
        "MAX_TOKENS": 1500,
        "TOP_P": 0.9,
    }
})
@pytest.mark.django_db
def test_extra_params_all_converted_to_lowercase(mock_settings):  # pylint: disable=unused-argument
    """
    Test that all AI_EXTENSIONS settings are converted to lowercase in extra_params.
    """
    processor = LitellmProcessor(config=None, user_session=None)

    assert "model" in processor.extra_params
    assert "api_key" in processor.extra_params
    assert "temperature" in processor.extra_params
    assert "max_tokens" in processor.extra_params
    assert "top_p" in processor.extra_params

    # Verify uppercase keys are not present
    assert "MODEL" not in processor.extra_params
    assert "API_KEY" not in processor.extra_params


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
        "API_KEY": "test-key",
    }
})
@pytest.mark.django_db
def test_extra_params_preserves_values(mock_settings):  # pylint: disable=unused-argument
    """
    Test that values in extra_params are preserved correctly.
    """
    processor = LitellmProcessor(config=None, user_session=None)

    assert processor.extra_params["model"] == "openai/gpt-4"
    assert processor.extra_params["api_key"] == "test-key"


# ============================================================================
# Process Method Tests
# ============================================================================


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_process_not_implemented(mock_settings):  # pylint: disable=unused-argument
    """
    Test that process method raises NotImplementedError.
    """
    processor = LitellmProcessor(config=None, user_session=None)

    with pytest.raises(NotImplementedError, match="Subclasses must implement process method"):
        processor.process()


# ============================================================================
# Get Provider Tests
# ============================================================================


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "openai/gpt-4",
    }
})
@pytest.mark.django_db
def test_get_provider_openai(mock_settings):  # pylint: disable=unused-argument
    """
    Test get_provider returns correct provider for OpenAI.
    """
    processor = LitellmProcessor(config=None, user_session=None)

    assert processor.get_provider() == "openai"


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "anthropic/claude-3",
    }
})
@pytest.mark.django_db
def test_get_provider_anthropic(mock_settings):  # pylint: disable=unused-argument
    """
    Test get_provider returns correct provider for Anthropic.
    """
    processor = LitellmProcessor(config=None, user_session=None)

    assert processor.get_provider() == "anthropic"


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "default": {
        "MODEL": "azure/gpt-4",
    }
})
@pytest.mark.django_db
def test_get_provider_azure(mock_settings):  # pylint: disable=unused-argument
    """
    Test get_provider returns correct provider for Azure.
    """
    processor = LitellmProcessor(config=None, user_session=None)

    assert processor.get_provider() == "azure"


# ============================================================================
# Integration Tests
# ============================================================================


@patch.object(settings, "AI_EXTENSIONS", new_callable=lambda: {
    "production": {
        "MODEL": "openai/gpt-4-turbo",
        "API_KEY": "prod-key",
        "TEMPERATURE": 0.3,
    }
})
@pytest.mark.django_db
def test_integration_custom_profile_with_tools(user):  # pylint: disable=redefined-outer-name,unused-argument
    """
    Integration test with custom profile and tools enabled.
    """
    config = {
        "LitellmProcessor": {
            "config": "production",
            "enabled_tools": ["roll_dice", "get_location_content"],
        }
    }
    processor = LitellmProcessor(config=config, user_session=None)

    assert processor.config_profile == "production"
    assert processor.provider == "openai"
    assert processor.extra_params["model"] == "openai/gpt-4-turbo"
    assert processor.extra_params["temperature"] == 0.3
    assert "tools" in processor.extra_params
    assert len(processor.extra_params["tools"]) == 2
