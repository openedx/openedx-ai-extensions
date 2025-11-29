"""
Open edX Content Extraction
"""

import logging

from opaque_keys.edx.keys import UsageKey

from openedx_ai_extensions.processors.component_extractors import COMPONENT_EXTRACTORS, extract_generic_info

logger = logging.getLogger(__name__)


class OpenEdXProcessor:
    """Handles Open edX content extraction"""

    def __init__(self, processor_config=None):
        processor_config = processor_config or {}

        # Find specific config using class name
        class_name = self.__class__.__name__
        self.config = processor_config.get(class_name, {})

    def process(self, context):
        """Process based on configured function"""
        function_name = self.config.get("function", "no_context")
        function = getattr(self, function_name)
        return function(context)

    def no_context(self, context):  # pylint: disable=unused-argument
        return {"display_name": "No context was provided."}

    def get_unit_content(self, context):
        """Extract unit content from Open edX modulestore"""
        try:
            # pylint: disable=import-error,import-outside-toplevel
            from xmodule.modulestore.django import modulestore

            location_id = context.get("extra_context", {}).get("unitId")

            if not location_id:
                return {"error": "Missing unitId in context"}

            # Get char_limit from config. Useful during development
            char_limit = self.config.get("char_limit", None)

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
