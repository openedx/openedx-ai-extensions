"""
Open edX Content Extraction
"""

import json
import logging

from django.conf import settings
from opaque_keys.edx.keys import UsageKey
from opaque_keys.edx.locator import CourseLocator

from openedx_ai_extensions.functions.decorators import llm_tool, register_instance
from openedx_ai_extensions.processors.component_extractors import (
    COMPONENT_EXTRACTORS,
    extract_generic_info,
    extract_problem_info,
)

logger = logging.getLogger(__name__)


class OpenEdXProcessor:
    """Handles Open edX content extraction"""

    def __init__(self, processor_config=None, location_id=None, course_id=None, user=None):
        processor_config = processor_config or {}

        # Find specific config using class name
        class_name = self.__class__.__name__
        self.config = processor_config.get(class_name, {})
        self.location_id = location_id
        self.course_id = course_id
        self.user = user

        # Register this instance for LLM function calls
        register_instance(self)

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        function_name = self.config.get("function", "no_context")
        function = getattr(self, function_name)

        return function(*args, **kwargs)

    def no_context(self, *args, **kwargs):
        """Return default message when no context is provided."""
        return {"display_name": "No context was provided."}

    @llm_tool(schema={
        "type": "function",
        "name": "get_location_content",  # responses needs to have this field.
        "function": {
            "name": "get_location_content",
            "description": (
                "Get published Open edX course content into an text format."
                "This function reads the *actual published content* of a course unit (or other"
                "course block) exactly as it is visible to the learner in the browser and"
                "converts it into a structured format suitable for LLM processing."

                "Use this function whenever an answer depends on the specific text, questions,"
                "instructions, or structure of the course content the user is currently viewing."
                "Do NOT rely on prior knowledge, assumptions, or summaries of the course."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location_id": {
                        "type": "string",
                        "description": (
                            "The string representation of the location ID, "
                            "if not provided uses the current location"
                        )
                    }
                },
                "required": []
            }
        }
    })
    def get_location_content(self, location_id=None):
        """Extract unit content from Open edX modulestore"""
        try:
            # pylint: disable=import-error,import-outside-toplevel
            from xmodule.modulestore.django import modulestore

            # Get char_limit from config. Useful during development
            char_limit = self.config.get("char_limit", None)
            location_id = location_id or self.location_id

            unit_key = UsageKey.from_string(location_id)
            store = modulestore()
            unit = store.get_item(unit_key)

            unit_info = {
                "unit_id": str(unit.location),
                "display_name": unit.display_name,
                "category": unit.category,
                "blocks": [],
            }

            for child_key in getattr(unit, "children", []):
                block_info = self._extract_block(store, child_key)
                if block_info:
                    unit_info["blocks"].append(block_info)

            if char_limit:
                self._truncate_unit_text(unit_info, char_limit)

            return unit_info

        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {"error": f"Error accessing content: {str(exc)}"}

    def _extract_block(self, store, block_key):
        """Helper to extract block info safely"""
        try:
            block = store.get_item(block_key)
            block_type = block.category.lower()
            extractor = COMPONENT_EXTRACTORS.get(block_type, extract_generic_info)
            if extractor is extract_problem_info:
                return extractor(block, self.config.get("show_answer", "auto"))
            return extractor(block)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(f"Could not load block {block_key}: {exc}")
            return None

    def _truncate_unit_text(self, unit_info, char_limit):
        """Helper to safely truncate text fields in unit blocks (dev-only)"""
        try:
            total_text = "".join(
                b.get("text", "") for b in unit_info["blocks"] if isinstance(b.get("text"), str)
            )

            if len(total_text) <= char_limit:
                return

            logger.debug("char_limit=%s triggered, truncating text fields safely", char_limit)

            blocks_with_text = [b for b in unit_info["blocks"] if isinstance(b.get("text"), str)]
            per_block = char_limit // len(blocks_with_text)

            for block in blocks_with_text:
                block["text"] = block["text"][:per_block]

            unit_info["truncated"] = True

        except Exception as trunc_err:  # pylint: disable=broad-exception-caught
            logger.debug("char_limit truncation skipped due to error: %s", trunc_err)

    @staticmethod
    def define_category(category):
        """Define a category processor"""
        if category == "chapter":
            return "section"
        if category == "sequential":
            return "subsection"
        if category == "vertical":
            return "unit"
        return "unknown"

    def get_course_outline(self, course_id=None, user=None):
        """Retrieve course outline structure (Sections > Subsections > Units)."""
        # pylint: disable=import-error,import-outside-toplevel
        from lms.djangoapps.course_blocks.api import get_course_blocks

        course_id = course_id or self.course_id
        user = user or self.user

        course_key = CourseLocator.from_string(course_id)
        course_usage_key = course_key.make_usage_key("course", "course")

        # 1. Get the BlockStructure object. This respects the user's permissions.
        block_structure = get_course_blocks(user, course_usage_key, include_completion=False)

        # 2. Serialize the structure, including the top-level 'course' block data.
        full_outline = self._serialize_block_structure_outline(block_structure)

        # Returning the single dictionary (which represents the course outline object) as JSON string
        return json.dumps(full_outline)

    def _serialize_block_structure_outline(self, block_structure):
        """
        Convert BlockStructure into:
        Sections (chapter) -> Subsections (sequential) -> Units (vertical)

        Output format:
        {
            "course_outline": [
                {
                    "display_name": "...",
                    "category": "section",
                    "subsections": [
                        {
                            "display_name": "...",
                            "category": "subsection",
                            "units": [
                                {
                                    "display_name": "...",
                                    "category": "unit"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        """
        root_key = block_structure.root_block_usage_key
        if not root_key:
            return []

        outline = []

        # -------- Chapters (Sections) --------
        for chapter_key in block_structure.get_children(root_key):
            category = block_structure.get_xblock_field(chapter_key, "category")
            if category != "chapter":
                continue

            chapter_info = {
                "display_name": block_structure.get_xblock_field(
                    chapter_key, "display_name"
                ),
                "category": self.define_category(category),
                "subsections": [],
            }

            # -------- Sequentials (Subsections) --------
            for sequential_key in block_structure.get_children(chapter_key):
                seq_category = block_structure.get_xblock_field(
                    sequential_key, "category"
                )
                if seq_category != "sequential":
                    continue

                sequential_info = {
                    "display_name": block_structure.get_xblock_field(
                        sequential_key, "display_name"
                    ),
                    "category": self.define_category(seq_category),
                    "units": [],
                }

                # -------- Verticals (Units) --------
                for vertical_key in block_structure.get_children(sequential_key):
                    vert_category = block_structure.get_xblock_field(
                        vertical_key, "category"
                    )
                    if vert_category != "vertical":
                        continue

                    vertical_info = {
                        "display_name": block_structure.get_xblock_field(
                            vertical_key, "display_name"
                        ),
                        "category": self.define_category(vert_category),
                    }

                    sequential_info["units"].append(vertical_info)

                if sequential_info["units"]:
                    chapter_info["subsections"].append(sequential_info)

            if chapter_info["subsections"]:
                outline.append(chapter_info)

        return outline

    @llm_tool(schema={
        "type": "function",
        "name": "get_context",  # responses needs to have this field.
        "function": {
              "name": "get_context",
              "description": "Get the context vars of the current Open edX location",
              }
    })
    def get_context(self):
        """Get the context of a given Open edX location."""
        return {
            "location_id": self.location_id,
            "course_id": self.course_id
        }

    @llm_tool(schema={
          "type": "function",
          "name": "get_location_link",  # responses needs to have this field.
          "function": {
              "name": "get_location_link",
              "description": "Get the URL of a given Open edX location",
              "parameters": {
                  "type": "object",
                  "properties": {
                      "location_id": {
                          "type": "string",
                          "description": (
                              "The string representation of the location ID, "
                              "if not provided uses the current location"
                          )
                      }
                  },
                  "required": []
              }
          }
      }
    )
    def get_location_link(self, location_id=None):
        """Helper to get the URL of a given location ID"""
        return (
            f"{settings.LEARNING_MICROFRONTEND_URL}/course/{self.course_id}/{location_id or self.location_id}"
        )
