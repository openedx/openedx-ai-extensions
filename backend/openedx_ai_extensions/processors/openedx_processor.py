"""
Open edX Content Extraction
"""
import logging
from opaque_keys.edx.keys import CourseKey, UsageKey
from xmodule.modulestore.django import modulestore

logger = logging.getLogger(__name__)


class OpenEdXProcessor:
    """Handles Open edX content extraction"""

    def __init__(self, processor_config=None):
        processor_config = processor_config or {}
        
        # Find specific config using class name
        class_name = self.__class__.__name__
        self.config = processor_config.get(class_name, {})

    def get_unit_content(self, unit_id):
        """Extract unit content from Open edX modulestore"""
        try:
            if not unit_id:
                return {"error": "Missing unit_id"}
            
            unit_key = UsageKey.from_string(unit_id)
            store = modulestore()
            unit = store.get_item(unit_key)
            
            unit_info = {
                "unit_id": str(unit.location),
                "display_name": unit.display_name,
                "category": unit.category,
                "blocks": []
            }
            
            if hasattr(unit, 'children') and unit.children:
                for child_key in unit.children:
                    try:
                        child = store.get_item(child_key)
                        block_info = {
                            "block_id": str(child.location),
                            "display_name": child.display_name,
                            "category": child.category,
                        }
                        
                        if child.category == 'html':
                            block_info["content"] = getattr(child, 'data', '')
                        elif child.category == 'problem':
                            block_info["content"] = getattr(child, 'data', '')
                        
                        unit_info["blocks"].append(block_info)
                    except Exception as e:
                        logger.warning(f"Could not load block {child_key}: {e}")
            
            return unit_info
            
        except Exception as e:
            return {"error": f"Error accessing content: {str(e)}"}
