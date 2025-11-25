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
                try:
                    block = store.get_item(child_key)
                    block_type = block.category.lower()
                    extractor = COMPONENT_EXTRACTORS.get(block_type, extract_generic_info)
                    info = extractor(block)
                    unit_info["blocks"].append(info)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"Could not load block {child_key}: {e}")

            # Optional char limit truncation
            if char_limit:
                import json
                s = json.dumps(unit_info)
                if len(s) > char_limit:
                    for block in unit_info["blocks"]:
                        if "text" in block and block["text"]:
                            block["text"] = block["text"][: char_limit // max(1, len(unit_info["blocks"]))]
                    unit_info["truncated"] = True

            return unit_info

        except Exception as e:  # pylint: disable=broad-exception-caught
            return {"error": f"Error accessing content: {str(e)}"}
