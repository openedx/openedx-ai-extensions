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
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


def _fake_get_config_from_file(
    cls, action: str, course_id: Optional[str] = None, unit_id: Optional[str] = None
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
    configs = None
    location = unit_id

    # Try to find a matching config file from proxy settings
    if location:
        for proxy in settings.AI_EXTENSIONS_MODEL_PROXY:
            location_regex = proxy.get("location_regex")
            file_path = proxy.get("file")
            full_path = os.path.join(os.path.dirname(__file__), file_path)

            if os.path.exists(full_path) and (re.match(location_regex, location)):
                with open(full_path, "r") as f:
                    configs = json.load(f)
                    break

    # If no config found, use the default file
    if configs is None:
        default_path = os.path.join(os.path.dirname(__file__), DEFAULT_CONFIG_FILE)
        with open(default_path, "r") as f:
            configs = json.load(f)

    # TODO: Remove verbose logging
    logger.debug(
        "AI CONFIG USED:\n%s",
        pprint.pformat(
            configs,
            indent=2,
        ),
    )

    return cls(
        action=action,
        course_id=course_id,
        unit_id=unit_id,
        orchestrator_class=configs["orchestrator_class"],
        processor_config=configs.get("processor_config", {}),
        actuator_config=configs.get("actuator_config", {}),
    )


def _fake_get_or_create_session(cls, user, curse_id: str, unit_id: str):
    """
    Fake method to simulate getting or creating a session.
    """
    path = os.path.join(
        os.path.dirname(__file__), f"session-{user.id}-{curse_id}-{unit_id}.json"
    )
    if os.path.exists(path):
        with open(path, "r") as f:
            session_data = json.load(f)
            user = User.objects.get(id=session_data["user_id"])
            return cls(
                id=session_data["id"],
                user=user,
                course_id=session_data["course_id"],
                unit_id=session_data.get("unit_id"),
                local_submission_id=session_data.get("local_submission_id"),
                remote_response_id=session_data.get("remote_response_id"),
                metadata=session_data.get("metadata", {}),
            )
    else:
        user = User.objects.get(id=user.id)
        new_session = cls(
            id=str(uuid4()),
            user=user,
            course_id=curse_id,
            unit_id=unit_id,
            local_submission_id=None,
            remote_response_id=None,
            metadata={},
        )
        with open(path, "w") as f:
            json.dump(
                {
                    "id": new_session.id,
                    "user_id": new_session.user.id,
                    "course_id": new_session.course_id,
                    "unit_id": new_session.unit_id,
                    "local_submission_id": new_session.local_submission_id,
                    "remote_response_id": new_session.remote_response_id,
                    "metadata": new_session.metadata,
                },
                f,
            )
        return new_session


def _fake_save_session(self):
    """
    Fake method to simulate saving a session.
    """
    path = os.path.join(
        os.path.dirname(__file__),
        f"session-{self.user.id}-{self.course_id}-{self.unit_id}.json",
    )
    with open(path, "w") as f:
        json.dump(
            {
                "id": self.id,
                "user_id": self.user.id,
                "course_id": self.course_id,
                "unit_id": self.unit_id,
                "local_submission_id": self.local_submission_id,
                "remote_response_id": self.remote_response_id,
                "metadata": self.metadata,
            },
            f,
        )


def _fake_delete_session(self):
    """
    Fake method to simulate deleting a session.
    """
    path = os.path.join(
        os.path.dirname(__file__),
        f"session-{self.user.id}-{self.course_id}-{self.unit_id}.json",
    )
    if os.path.exists(path):
        os.remove(path)
