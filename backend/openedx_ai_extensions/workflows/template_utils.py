"""
Utilities for discovering, loading, and validating workflow templates.

Templates are read-only JSON5 files stored on disk (allowing comments).
Security: Only load from configured directories to prevent path traversal.
"""
import logging
from pathlib import Path
from typing import Optional

import json5
from django.conf import settings
from jsonmerge import merge
from jsonschema import Draft7Validator

logger = logging.getLogger(__name__)


# JSON Schema for workflow configuration validation (schema version 1.0)
WORKFLOW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["schema_version", "orchestrator_class", "processor_config", "actuator_config"],
    "properties": {
        "schema_version": {
            "type": "string",
            "const": "1.0",
            "description": "Schema version 1.0"
        },
        "orchestrator_class": {
            "type": "string",
            "minLength": 1,
            "description": "Name of the orchestrator class to use"
        },
        "processor_config": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": True,
            "description": "Configuration for processors - must contain at least one processor"
        },
        "actuator_config": {
            "type": "object",
            "required": ["UIComponents"],
            "properties": {
                "UIComponents": {
                    "type": "object",
                    "required": ["request", "response"],
                    "properties": {
                        "request": {
                            "type": "object",
                            "description": "UI request configuration"
                        },
                        "response": {
                            "type": "object",
                            "description": "UI response configuration"
                        }
                    },
                    "additionalProperties": True,
                    "description": "UI components configuration"
                }
            },
            "additionalProperties": True,
            "description": "Configuration for actuators (UI components, etc)"
        }
    },
    "additionalProperties": True
}


def get_template_directories() -> list[Path]:
    """
    Get list of allowed template directories from settings.

    Returns:
        List of Path objects pointing to template directories
    """

    # Get from settings if available
    template_dirs = getattr(settings, "WORKFLOW_TEMPLATE_DIRS")

    # Convert to Path objects and ensure they exist
    paths = []
    for dir_path in template_dirs:
        path = Path(dir_path).resolve()
        if path.exists() and path.is_dir():
            paths.append(path)
        else:
            logger.warning(f"Template directory does not exist: {dir_path}")

    return paths


def is_safe_template_path(template_path: str) -> bool:
    """
    Verify that a template path is safe (no path traversal attacks).

    Args:
        template_path: Relative path to template file

    Returns:
        True if path is safe, False otherwise
    """
    if not template_path:
        return False

    # Check for path traversal attempts
    if ".." in template_path or template_path.startswith("/"):
        logger.warning(f"Rejected unsafe template path: {template_path}")
        return False

    # Verify the file exists in one of the allowed directories
    template_dirs = get_template_directories()
    for base_dir in template_dirs:
        full_path = (base_dir / template_path).resolve()

        # Ensure resolved path is still within the allowed directory
        try:
            full_path.relative_to(base_dir)
            if full_path.exists() and full_path.is_file():
                return True
        except ValueError:
            # Path is outside the base directory
            continue

    return False


def discover_templates() -> list[tuple[str, str]]:
    """
    Discover all available workflow templates.

    Returns:
        List of (relative_path, display_name) tuples for Django choices
    """
    templates = []
    template_dirs = get_template_directories()

    for base_dir in template_dirs:
        # Find all .json files recursively
        for json_file in base_dir.rglob("*.json"):
            try:
                # Get relative path from base directory
                rel_path = json_file.relative_to(base_dir)

                # Create display name (remove .json, replace slashes with dots)
                display_name = str(rel_path.with_suffix("")).replace("/", ".")

                templates.append((str(rel_path), display_name))
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Error processing template {json_file}: {e}")

    # Sort by display name
    templates.sort(key=lambda x: x[1])

    return templates


def load_template(template_path: str) -> Optional[dict]:
    """
    Load a workflow template from disk.

    Supports JSON5 format (allows comments, trailing commas, etc).

    Args:
        template_path: Relative path to template file

    Returns:
        Template data as dict, or None if not found/invalid
    """
    if not is_safe_template_path(template_path):
        logger.error(f"Attempted to load unsafe template path: {template_path}")
        return None

    template_dirs = get_template_directories()

    for base_dir in template_dirs:
        full_path = base_dir / template_path
        if full_path.exists():
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json5.load(f)

                logger.info(f"Loaded template: {template_path}")
                return data
            except ValueError as e:
                # json5 raises ValueError for invalid JSON5
                logger.error(f"Invalid JSON5 in template {template_path}: {e}")
                return None
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Error loading template {template_path}: {e}")
                return None

    logger.error(f"Template not found: {template_path}")
    return None


def parse_json5_string(json5_string: str) -> dict:
    """
    Parse a JSON5 string into a dict.

    Allows comments, trailing commas, etc.

    Args:
        json5_string: JSON5-formatted string

    Returns:
        Parsed dict

    Raises:
        json5.JSON5DecodeError: If string is invalid JSON5
    """
    if not json5_string or not json5_string.strip():
        return {}

    return json5.loads(json5_string)


def merge_template_with_patch(base_template: dict, patch: dict) -> dict:
    """
    Merge a base template with a JSON patch.

    Uses RFC 7386 JSON Merge Patch via jsonmerge library.

    Args:
        base_template: Base template configuration
        patch: JSON patch to apply

    Returns:
        Merged configuration
    """
    if not patch:
        return base_template.copy()

    try:
        # Use jsonmerge for RFC 7386 merge patch
        merged = merge(base_template, patch)
        return merged
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error merging template with patch: {e}")
        # Return base template on error
        return base_template.copy()


def validate_workflow_config(config: dict) -> tuple[bool, list[str]]:
    """
    Validate a workflow configuration against the JSON schema.

    Enforces schema version 1.0 requirements.

    Args:
        config: Configuration to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    if config is None:
        return False, ["config is null (base template missing or failed to load)"]

    if not isinstance(config, dict):
        return False, [f"config must be an object/dict, got {type(config).__name__}"]

    # JSON Schema validation (schema version 1.0)
    validator = Draft7Validator(WORKFLOW_SCHEMA)
    schema_errors = list(validator.iter_errors(config))

    for error in schema_errors:
        # Format error message with path
        path = ".".join(str(p) for p in error.path) if error.path else "root"
        errors.append(f"{path}: {error.message}")

    # Semantic validation
    semantic_errors = _validate_semantics(config)
    errors.extend(semantic_errors)

    is_valid = len(errors) == 0

    return is_valid, errors


def _validate_semantics(config: dict) -> list[str]:
    """
    Perform semantic validation beyond JSON schema.

    Validates Python identifier constraints and nested structure requirements
    that are not easily expressed in JSON schema.

    Args:
        config: Configuration to validate

    Returns:
        List of error messages
    """
    errors = []

    # Check orchestrator_class is a valid Python identifier
    orchestrator_class = config.get("orchestrator_class", "")
    if not orchestrator_class:
        errors.append("orchestrator_class cannot be empty")
    elif not orchestrator_class.replace("_", "").replace(".", "").isalnum():
        errors.append(f"orchestrator_class '{orchestrator_class}' is not a valid Python identifier")

    # Check processor_config structure (required by schema 1.0)
    processor_config = config.get("processor_config", {})
    if not isinstance(processor_config, dict):
        errors.append("processor_config must be an object")
    elif len(processor_config) == 0:
        errors.append("processor_config must contain at least one processor")
    else:
        # Validate that all processor values are objects
        for processor_name, processor_value in processor_config.items():
            if not isinstance(processor_value, dict):
                errors.append(f"processor_config.{processor_name} must be an object")

    # Check actuator_config structure (required by schema 1.0)
    actuator_config = config.get("actuator_config", {})
    if not isinstance(actuator_config, dict):
        errors.append("actuator_config must be an object")
    else:
        ui_components = actuator_config.get("UIComponents")
        if ui_components is not None:
            if not isinstance(ui_components, dict):
                errors.append("actuator_config.UIComponents must be an object")
            else:
                # Check request and response structures
                request = ui_components.get("request")
                if request is not None and not isinstance(request, dict):
                    errors.append("actuator_config.UIComponents.request must be an object")

                response = ui_components.get("response")
                if response is not None and not isinstance(response, dict):
                    errors.append("actuator_config.UIComponents.response must be an object")

    return errors


def get_effective_config(base_filepath: str, content_patch: dict) -> Optional[dict]:
    """
    Get the effective configuration by merging base template with patch.

    This is the main function used by AIWorkflowProfile.

    Args:
        base_filepath: Relative path to base template
        content_patch: JSON patch to apply

    Returns:
        Effective configuration, or None if base template cannot be loaded
    """
    base_template = load_template(base_filepath)
    if base_template is None:
        return None

    return merge_template_with_patch(base_template, content_patch)
