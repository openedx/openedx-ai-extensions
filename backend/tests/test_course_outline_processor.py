"""
Tests for CourseOutlineProcessor.
"""

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from opaque_keys.edx.keys import CourseKey

from openedx_ai_extensions.processors import CourseOutlineProcessor

mock_xmodule = MagicMock()
mock_modulestore_django = MagicMock()
mock_xmodule.modulestore.django = mock_modulestore_django
sys.modules["xmodule"] = mock_xmodule
sys.modules["xmodule.modulestore"] = mock_xmodule.modulestore
sys.modules["xmodule.modulestore.django"] = mock_modulestore_django


@pytest.fixture
def processor():
    """Fixture for CourseOutlineProcessor instance."""
    return CourseOutlineProcessor()


@pytest.fixture
def mock_course_key():
    """Fixture for a mocked CourseKey."""
    return MagicMock(spec=CourseKey)


def create_mock_block(
    display_name, category, children=None, visible_to_staff_only=False, start=None
):
    """Helper to create a mock XBlock/Item with necessary attributes."""
    block = MagicMock()
    block.display_name = display_name
    block.category = category
    block.children = children or []
    block.visible_to_staff_only = visible_to_staff_only
    block.start = start
    return block


# ============================================================================
# Unit Tests
# ============================================================================

def test_initialization():
    """Test proper initialization of the processor."""
    config = {"CourseOutlineProcessor": {"function": "custom_func"}}
    proc = CourseOutlineProcessor(processor_config=config)
    assert proc.config == {"function": "custom_func"}


def test_define_category(processor):  # pylint: disable=redefined-outer-name
    """Test the category mapping logic."""
    assert processor.define_category("chapter") == "section"
    assert processor.define_category("sequential") == "subsection"
    assert processor.define_category("vertical") == "unit"
    assert processor.define_category("video") == "unknown"


def test_process_dispatch(processor):  # pylint: disable=redefined-outer-name
    """Test that .process() calls the configured function."""
    with patch.object(processor, "get_course_outline") as mock_get_outline:
        mock_get_outline.return_value = {"status": "ok"}

        result = processor.process({"course_id": "course-v1:test"})

        assert result == {"status": "ok"}
        mock_get_outline.assert_called_once_with({"course_id": "course-v1:test"})


# ============================================================================
# Visibility Logic Tests (_is_block_visible)
# ============================================================================

def test_is_block_visible_standard(processor):  # pylint: disable=redefined-outer-name
    """Test a standard visible block."""
    block = create_mock_block("Test", "vertical")
    # pylint: disable=protected-access
    assert processor._is_block_visible(block) is True


def test_is_block_visible_staff_only(processor):  # pylint: disable=redefined-outer-name
    """Test that staff-only blocks are hidden."""
    block = create_mock_block("Hidden", "vertical", visible_to_staff_only=True)
    # pylint: disable=protected-access
    assert processor._is_block_visible(block) is False


def test_is_block_visible_future_start_date(processor):  # pylint: disable=redefined-outer-name
    """Test that blocks with future start dates are hidden."""
    future_date = datetime.now(timezone.utc) + timedelta(days=1)
    block = create_mock_block("Future", "vertical", start=future_date)
    # pylint: disable=protected-access
    assert processor._is_block_visible(block) is False


def test_is_block_visible_past_start_date(processor):  # pylint: disable=redefined-outer-name
    """Test that blocks with past start dates are visible."""
    past_date = datetime.now(timezone.utc) - timedelta(days=1)
    block = create_mock_block("Past", "vertical", start=past_date)
    # pylint: disable=protected-access
    assert processor._is_block_visible(block) is True


# ============================================================================
# Get Course Outline Tests (Main Logic)
# ============================================================================

def test_get_course_outline_missing_id(processor):  # pylint: disable=redefined-outer-name
    """Test error when course_id is missing."""
    result = processor.get_course_outline({})
    assert "error" in result
    assert "Missing course_id" in result["error"]


@patch("openedx_ai_extensions.processors.openedx.course_outline_processor.CourseKey")
def test_get_course_outline_success(
    mock_course_key_cls, processor  # pylint: disable=redefined-outer-name
):
    """
    Test successful retrieval of a full hierarchy:
    Course -> Chapter (Section) -> Sequential (Subsection) -> Vertical (Unit)
    """
    # 1. Setup Mocks
    mock_key = MagicMock()
    mock_course_key_cls.from_string.return_value = mock_key

    # Mock the modulestore and the store instance
    with patch("xmodule.modulestore.django.modulestore") as mock_modulestore_func:
        mock_store = MagicMock()
        mock_modulestore_func.return_value = mock_store

        # 2. Build Block Hierarchy
        # Vertical (Unit)
        vertical = create_mock_block("Test Unit", "vertical")

        # Sequential (Subsection) -> contains Vertical
        sequential = create_mock_block("Test Subsection", "sequential", children=["vert-1"])

        # Chapter (Section) -> contains Sequential
        chapter = create_mock_block("Test Section", "chapter", children=["seq-1"])

        # Course -> contains Chapter
        course = create_mock_block("Course Root", "course", children=["chap-1"])

        # 3. Configure store.get_course and store.get_item
        mock_store.get_course.return_value = course

        def get_item_side_effect(location):
            if location == "chap-1":
                return chapter
            if location == "seq-1":
                return sequential
            if location == "vert-1":
                return vertical
            return None

        mock_store.get_item.side_effect = get_item_side_effect

        # 4. Execute
        context = {"course_id": "course-v1:Test+Course"}
        result = processor.get_course_outline(context)

        # 5. Assertions
        assert "course_outline" in result
        outline = result["course_outline"]

        # Check Structure
        assert len(outline) == 1
        section = outline[0]
        assert section["display_name"] == "Test Section"
        assert section["category"] == "section"

        assert len(section["subsections"]) == 1
        subsection = section["subsections"][0]
        assert subsection["display_name"] == "Test Subsection"
        assert subsection["category"] == "subsection"

        assert len(subsection["units"]) == 1
        unit = subsection["units"][0]
        assert unit["display_name"] == "Test Unit"
        assert unit["category"] == "unit"


@patch("openedx_ai_extensions.processors.openedx.course_outline_processor.CourseKey")
def test_get_course_outline_filters_empty_sections(
    mock_course_key_cls, processor  # pylint: disable=redefined-outer-name
):
    """
    Test that the processor does not include sections or subsections
    if they end up empty (e.g. because children are hidden).
    """
    mock_key = MagicMock()
    mock_course_key_cls.from_string.return_value = mock_key

    with patch("xmodule.modulestore.django.modulestore") as mock_modulestore_func:
        mock_store = MagicMock()
        mock_modulestore_func.return_value = mock_store

        # Hierarchy: Chapter -> Sequential (Hidden) -> Vertical
        # The Sequential is hidden, so the Chapter becomes empty, so the Outline should be empty.

        vertical = create_mock_block("Unit", "vertical")
        sequential = create_mock_block(
            "Hidden Subsection",
            "sequential",
            children=["vert-1"],
            visible_to_staff_only=True
        )
        chapter = create_mock_block("Section", "chapter", children=["seq-1"])
        course = create_mock_block("Course", "course", children=["chap-1"])

        mock_store.get_course.return_value = course

        def get_item_side_effect(location):
            if location == "chap-1":
                return chapter
            if location == "seq-1":
                return sequential
            if location == "vert-1":
                return vertical
            return None

        mock_store.get_item.side_effect = get_item_side_effect

        result = processor.get_course_outline({"course_id": "course-v1:id"})

        assert result["course_outline"] == []


@patch("openedx_ai_extensions.processors.openedx.course_outline_processor.CourseKey")
def test_get_course_outline_exception_handling(
    mock_course_key_cls, processor  # pylint: disable=redefined-outer-name
):
    """Test that exceptions during processing are caught and returned as errors."""
    mock_course_key_cls.from_string.side_effect = Exception("Invalid Key")

    result = processor.get_course_outline({"course_id": "bad-id"})

    assert "error" in result
    assert "Error accessing course outline" in result["error"]
    assert "Invalid Key" in result["error"]
