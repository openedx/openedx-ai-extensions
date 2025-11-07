import logging
import os
import json

logger = logging.getLogger(__name__)

def _search_user_info_in_file(user_id, location):
    """Search for user info in a given file by user ID."""
    full_path = os.path.join(os.path.dirname(__file__), "workflows", "configs", f"{location}-{user_id}.yaml")
    if os.path.exists(full_path):
        with open(full_path, "r") as file:
            content = file.read()
            return json.loads(content)
    return None

def _update_file_with_user_info(user_id, location, data):
    """Update a file with user information."""
    full_path = os.path.join(os.path.dirname(__file__), "workflows", "configs", f"{location}-{user_id}.yaml")
    with open(full_path, "w") as file:
        file.write(json.dumps(data))
