"""
Tests for the LitellmProcessor base class.
"""

import pytest
from django.conf import settings
from django.test import override_settings

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor


@pytest.fixture
def basic_config():
    """
    Return a basic processor config.
    """
    return {
        "LitellmProcessor": {
            "config": "default",
        }
    }


@pytest.fixture
def config_with_mcp():
    """
    Return a processor config with MCP configs.
    """
    return {
        "LitellmProcessor": {
            "config": "default",
            "mcp_configs": ["server1", "server2"],
        }
    }


# ============================================================================
# LitellmProcessor Initialization Tests
# ============================================================================


@pytest.mark.django_db
def test_litellm_processor_initialization_basic(basic_config):  # pylint: disable=redefined-outer-name
    """
    Test LitellmProcessor initialization with basic config.
    """
    processor = LitellmProcessor(config=basic_config)

    assert processor.config == basic_config["LitellmProcessor"]
    assert processor.config_profile == "default"
    assert processor.api_key == settings.AI_EXTENSIONS["default"]["API_KEY"]
    assert processor.model == settings.AI_EXTENSIONS["default"]["LITELLM_MODEL"]
    assert processor.mcp_configs == {}


@pytest.mark.django_db
def test_litellm_processor_initialization_with_timeout():
    """
    Test that timeout is properly extracted to extra_params.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
        }
    }
    processor = LitellmProcessor(config=config)

    assert "timeout" in processor.extra_params
    assert processor.extra_params["timeout"] == settings.AI_EXTENSIONS["default"]["TIMEOUT"]


@pytest.mark.django_db
def test_litellm_processor_initialization_with_temperature():
    """
    Test that temperature is properly extracted to extra_params.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
        }
    }
    processor = LitellmProcessor(config=config)

    assert "temperature" in processor.extra_params
    assert processor.extra_params["temperature"] == settings.AI_EXTENSIONS["default"]["TEMPERATURE"]


@pytest.mark.django_db
def test_litellm_processor_initialization_with_max_tokens():
    """
    Test that max_tokens is properly extracted to extra_params.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
        }
    }
    processor = LitellmProcessor(config=config)

    assert "max_tokens" in processor.extra_params
    assert processor.extra_params["max_tokens"] == settings.AI_EXTENSIONS["default"]["MAX_TOKENS"]


# ============================================================================
# MCP Configs Tests
# ============================================================================


@pytest.mark.django_db
@override_settings(
    AI_EXTENSIONS_MCP_CONFIGS={
        "server1": {
            "command": "uvx",
            "args": ["--from", "mcp-server-fetch", "mcp-server-fetch"],
            "env": {},
        },
        "server2": {
            "command": "python",
            "args": ["-m", "mcp_server"],
            "env": {"API_KEY": "test-key"},
        },
        "server3": {
            "command": "node",
            "args": ["server.js"],
            "env": {},
        },
    }
)
def test_litellm_processor_mcp_configs_filters_allowed_configs(config_with_mcp):  # pylint: disable=redefined-outer-name
    """
    Test that MCP configs are properly filtered based on allowed list.
    Only server1 and server2 should be included, not server3.
    """
    processor = LitellmProcessor(config=config_with_mcp)

    # Check mcp_configs contains only allowed servers
    assert len(processor.mcp_configs) == 2
    assert "server1" in processor.mcp_configs
    assert "server2" in processor.mcp_configs
    assert "server3" not in processor.mcp_configs

    # Verify the configs match settings
    assert processor.mcp_configs["server1"]["command"] == "uvx"
    assert processor.mcp_configs["server2"]["command"] == "python"


@pytest.mark.django_db
@override_settings(
    AI_EXTENSIONS_MCP_CONFIGS={
        "server1": {
            "command": "uvx",
            "args": ["--from", "mcp-server-fetch", "mcp-server-fetch"],
            "env": {},
        },
        "server2": {
            "command": "python",
            "args": ["-m", "mcp_server"],
            "env": {"API_KEY": "test-key"},
        },
    }
)
def test_litellm_processor_mcp_configs_adds_tools_to_extra_params(
    config_with_mcp,
):  # pylint: disable=redefined-outer-name
    """
    Test that MCP configs are properly added to extra_params as tools.
    """
    processor = LitellmProcessor(config=config_with_mcp)

    # Check tools are added to extra_params
    assert "tools" in processor.extra_params
    assert isinstance(processor.extra_params["tools"], list)
    assert len(processor.extra_params["tools"]) == 2

    # Verify tool structure for server1
    server1_tool = next(
        (tool for tool in processor.extra_params["tools"] if tool["server_label"] == "server1"),
        None,
    )
    assert server1_tool is not None
    assert server1_tool["type"] == "mcp"
    assert server1_tool["command"] == "uvx"
    assert server1_tool["args"] == ["--from", "mcp-server-fetch", "mcp-server-fetch"]
    assert server1_tool["env"] == {}

    # Verify tool structure for server2
    server2_tool = next(
        (tool for tool in processor.extra_params["tools"] if tool["server_label"] == "server2"),
        None,
    )
    assert server2_tool is not None
    assert server2_tool["type"] == "mcp"
    assert server2_tool["command"] == "python"
    assert server2_tool["args"] == ["-m", "mcp_server"]
    assert server2_tool["env"] == {"API_KEY": "test-key"}


@pytest.mark.django_db
@override_settings()
def test_litellm_processor_no_mcp_configs_in_settings(basic_config):  # pylint: disable=redefined-outer-name
    """
    Test that processor works correctly when AI_EXTENSIONS_MCP_CONFIGS is not in settings.
    """
    # Ensure AI_EXTENSIONS_MCP_CONFIGS is not set
    # override_settings without AI_EXTENSIONS_MCP_CONFIGS ensures it's not present
    processor = LitellmProcessor(config=basic_config)

    # Should initialize without errors
    assert processor.mcp_configs == {}
    assert "tools" not in processor.extra_params


@pytest.mark.django_db
@override_settings(
    AI_EXTENSIONS_MCP_CONFIGS={
        "server1": {
            "command": "uvx",
            "args": ["--from", "mcp-server-fetch", "mcp-server-fetch"],
            "env": {},
        },
    }
)
def test_litellm_processor_mcp_configs_empty_allowed_list():
    """
    Test that no MCP configs are added when allowed list is empty.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
            "mcp_configs": [],  # Empty list
        }
    }
    processor = LitellmProcessor(config=config)

    # Should not add any configs or tools
    assert processor.mcp_configs == {}
    assert "tools" not in processor.extra_params


@pytest.mark.django_db
@override_settings(
    AI_EXTENSIONS_MCP_CONFIGS={
        "server1": {
            "command": "uvx",
            "args": ["--from", "mcp-server-fetch", "mcp-server-fetch"],
            "env": {},
        },
    }
)
def test_litellm_processor_mcp_configs_not_specified():
    """
    Test that no MCP configs are added when mcp_configs is not in config.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
            # No mcp_configs key
        }
    }
    processor = LitellmProcessor(config=config)

    # Should not add any configs or tools
    assert processor.mcp_configs == {}
    assert "tools" not in processor.extra_params


@pytest.mark.django_db
@override_settings(
    AI_EXTENSIONS_MCP_CONFIGS={
        "server1": {
            "command": "uvx",
            "args": ["--from", "mcp-server-fetch", "mcp-server-fetch"],
            "env": {},
        },
    }
)
def test_litellm_processor_mcp_configs_nonexistent_server():
    """
    Test that processor handles gracefully when requested server doesn't exist in settings.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
            "mcp_configs": ["nonexistent_server"],
        }
    }
    processor = LitellmProcessor(config=config)

    # Should initialize without errors but not add any configs
    assert processor.mcp_configs == {}
    assert processor.extra_params.get("tools", []) == []


# ============================================================================
# Process Method Tests
# ============================================================================


@pytest.mark.django_db
def test_litellm_processor_process_not_implemented():
    """
    Test that process() raises NotImplementedError as it must be implemented by subclasses.
    """
    config = {
        "LitellmProcessor": {
            "config": "default",
        }
    }
    processor = LitellmProcessor(config=config)

    with pytest.raises(NotImplementedError, match="Subclasses must implement process method"):
        processor.process()
