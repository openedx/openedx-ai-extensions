"""
Open edX Course Outline Extraction
"""

import logging
from datetime import datetime, timezone

from opaque_keys.edx.keys import CourseKey

logger = logging.getLogger(__name__)


class CourseOutlineProcessor:
    """Processor that retrieves the course outline: sections > subsections > units"""

    def __init__(self, processor_config=None):
        processor_config = processor_config or {}
        class_name = self.__class__.__name__
        self.config = processor_config.get(class_name, {})

    def process(self, context):
        """Main entry point"""
        function_name = self.config.get("function", "get_course_outline")
        function = getattr(self, function_name)
        return function(context)

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

    def _is_block_visible(self, block):
        """Return False if block should be filtered out."""
        now = datetime.now(timezone.utc)

        if getattr(block, "visible_to_staff_only", False):
            return False
        start = getattr(block, "start", None)
        if start and start > now:
            return False
        return True

    def get_course_outline(self, context):
        """Retrieve & filter course outline."""
        try:
            from xmodule.modulestore.django import modulestore  # pylint: disable=import-error, import-outside-toplevel

            course_id = context.get("course_id")
            if not course_id:
                return {"error": "Missing course_id in context"}

            course_key = CourseKey.from_string(course_id)
            store = modulestore()
            course = store.get_course(course_key)

            outline = []

            # Chapters
            for chapter_loc in course.children:
                chapter = store.get_item(chapter_loc)
                if not self._is_block_visible(chapter):
                    continue

                chapter_info = {
                    "display_name": chapter.display_name,
                    "category": self.define_category(chapter.category),
                    "subsections": [],
                }

                # Sequentials
                for sequential_loc in chapter.children:
                    sequential = store.get_item(sequential_loc)
                    if not self._is_block_visible(sequential):
                        continue

                    sequential_info = {
                        "display_name": sequential.display_name,
                        "category": self.define_category(sequential.category),
                        "units": [],
                    }

                    # Verticals
                    for vertical_loc in sequential.children:
                        vertical = store.get_item(vertical_loc)
                        if not self._is_block_visible(vertical):
                            continue

                        vertical_info = {
                            "display_name": vertical.display_name,
                            "category": self.define_category(vertical.category),
                        }

                        sequential_info["units"].append(vertical_info)

                    if sequential_info["units"]:
                        chapter_info["subsections"].append(sequential_info)

                if chapter_info["subsections"]:
                    outline.append(chapter_info)

            return {"course_outline": outline}

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to get course outline")
            return {"error": f"Error accessing course outline: {exc}"}
