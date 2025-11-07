"""
Utility functions for OpenEdX AI Extensions.
"""
import json
import os
import re
from typing import Optional

from django.conf import settings


def _fake_get_config_from_file(cls, action: str, course_id: Optional[str] = None, unit_id: Optional[str] = None):
    """
    Fake method to simulate loading config from file.
    """
    location = unit_id

    for proxy in settings.AI_EXTENSIONS_MODEL_PROXY:
        location_regex = proxy.get("location_regex")
        file_path = proxy.get("file")
        full_path = os.path.join(os.path.dirname(__file__), "workflows", file_path)

        if os.path.exists(full_path) and (location == location_regex or re.match(location_regex, location)):
            with open(full_path, "r") as f:
                configs = json.load(f)
                break

    return cls(
        action=action,
        course_id=course_id,
        unit_id=unit_id,
        orchestrator_class=configs["orchestrator_class"],
        processor_config=configs.get("processor_config", {}),
        actuator_config=configs.get("actuator_config", {}),
    )
