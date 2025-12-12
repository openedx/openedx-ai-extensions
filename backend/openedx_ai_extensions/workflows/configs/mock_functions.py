"""
This module replaces calling a model temporarily.
Once the interfaces for configs are more stable they will move into a proper model.
"""

import json
import logging
import os
import pprint
import re
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


def _fake_get_config_from_file(
    cls, action: str, course_id: Optional[str] = None, location_id: Optional[str] = None
):
    """
    Fake method to simulate loading config from file.

    To use this, set the AI_EXTENSIONS_MODEL_PROXY in your production.py settings
    or any other method for dev instances.

    E.g:
    AI_EXTENSIONS_MODEL_PROXY = [
        {
            "location_regex": ".*",
            "file": "anthropic_hello.json",
        },
    ]
    """
    # Define the default configuration file path
    DEFAULT_CONFIG_FILE = "default.json"
    if getattr(settings, "SERVICE_VARIANT", "lms") == "cms":
        DEFAULT_CONFIG_FILE = "default_cms.json"

    configs = None
    config_filename = None
    location = location_id

    # Try to find a matching config file from proxy settings
    if location:
        for proxy in settings.AI_EXTENSIONS_MODEL_PROXY:
            location_regex = proxy.get("location_regex")
            file_path = proxy.get("file")
            full_path = os.path.join(os.path.dirname(__file__), file_path)

            if os.path.exists(full_path) and (re.match(location_regex, location)):
                with open(full_path, "r") as f:
                    configs = json.load(f)
                    # Extract filename without extension (e.g., "openai_threads" from "openai_threads.json")
                    config_filename = os.path.splitext(os.path.basename(file_path))[0]
                    break

    # If no config found, use the default file
    if configs is None:
        default_path = os.path.join(os.path.dirname(__file__), DEFAULT_CONFIG_FILE)
        with open(default_path, "r") as f:
            configs = json.load(f)
            config_filename = os.path.splitext(DEFAULT_CONFIG_FILE)[0]

    # TODO: Remove verbose logging
    logger.debug(
        "AI CONFIG USED:\n%s",
        pprint.pformat(
            configs,
            indent=2,
        ),
    )

    # Store the config filename in processor_config metadata
    processor_config = configs.get("processor_config", {})
    processor_config["_config_filename"] = config_filename

    return cls(
        action=action,
        course_id=course_id,
        location_id=location_id,
        orchestrator_class=configs["orchestrator_class"],
        processor_config=processor_config,
        actuator_config=configs.get("actuator_config", {}),
    )
