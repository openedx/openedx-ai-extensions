"""
Tests for OpenEdXProcessor content extraction and serialization.
"""
# pylint: disable=redefined-outer-name

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from openedx_ai_extensions.processors.openedx.openedx_processor import OpenEdXProcessor

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_edx_imports():
    """
    Mock the internal edX imports used inside methods.
    """
    with patch.dict(sys.modules, {
        "xmodule": MagicMock(),
        "xmodule.modulestore": MagicMock(),
        "xmodule.modulestore.django": MagicMock(),
        "lms": MagicMock(),
        "lms.djangoapps": MagicMock(),
        "lms.djangoapps.course_blocks": MagicMock(),
        "lms.djangoapps.course_blocks.api": MagicMock(),
        "openedx": MagicMock(),
        "openedx.core": MagicMock(),
        "openedx.core.djangoapps": MagicMock(),
        "openedx.core.djangoapps.models": MagicMock(),
        "openedx.core.djangoapps.models.course_details": MagicMock(),
    }):
        yield


@pytest.fixture
def mock_keys():
    """
    Mock opaque_keys to avoid InvalidKeyError and 'import-outside-toplevel' issues.
    """
    with patch("openedx_ai_extensions.processors.openedx.openedx_processor.UsageKey") as mock_usage:
        with patch("openedx_ai_extensions.processors.openedx.openedx_processor.CourseLocator") as mock_course:
            # Setup default return values for keys so they act like valid objects
            mock_usage.from_string.return_value = MagicMock(name="UnitUsageKey")
            mock_course.from_string.return_value = MagicMock(name="CourseKey")
            yield mock_usage, mock_course


@pytest.fixture
def processor():
    """Fixture for OpenEdXProcessor."""
    return OpenEdXProcessor()


@pytest.fixture
def mock_block_structure():
    """Fixture for generic block structure."""
    bs = MagicMock()
    bs.root_block_usage_key = "course-root"
    return bs


def configure_mock_bs(mock_bs, children_map, fields_map):
    """Helper to configure block structure side effects."""
    mock_bs.get_children.side_effect = lambda key: children_map.get(key, [])
    mock_bs.get_xblock_field.side_effect = lambda key, field: fields_map.get((key, field))


# ============================================================================
# Tests: Content Extraction
# ============================================================================

def test_get_location_content_success(mock_edx_imports, mock_keys):
    """Test successful unit content extraction."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from xmodule.modulestore.django import modulestore

    mock_unit = MagicMock()
    mock_unit.location = "course-key-1"
    mock_unit.display_name = "Test Unit"
    mock_unit.category = "vertical"
    mock_unit.children = ["block-1"]

    mock_store = modulestore.return_value
    mock_store.get_item.return_value = mock_unit

    test_processor = OpenEdXProcessor()

    with patch.object(test_processor, '_extract_block', return_value={"text": "Block Content"}):
        result = test_processor.get_location_content("loc-id")

    assert result.get("display_name") == "Test Unit"
    assert len(result["blocks"]) == 1
    assert result["blocks"][0]["text"] == "Block Content"


def test_get_location_content_truncation(mock_edx_imports, mock_keys):
    """Test that text is truncated when char_limit is exceeded."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from xmodule.modulestore.django import modulestore

    config = {"OpenEdXProcessor": {"char_limit": 10}}
    test_processor = OpenEdXProcessor(processor_config=config)

    mock_store = modulestore.return_value
    mock_unit = MagicMock()
    mock_unit.location = "loc"
    mock_unit.display_name = "Unit"
    mock_unit.category = "vertical"
    mock_unit.children = ["b1", "b2"]
    mock_store.get_item.return_value = mock_unit

    with patch.object(test_processor, '_extract_block') as mock_extract:
        mock_extract.side_effect = [
            {"text": "1234567890"},
            {"text": "1234567890"},
        ]

        result = test_processor.get_location_content("loc")

    assert result.get("truncated") is True
    assert len(result["blocks"][0]["text"]) == 5
    assert len(result["blocks"][1]["text"]) == 5


def test_get_location_content_error_handling(mock_edx_imports, mock_keys):
    """Test that exceptions are caught and returned as errors."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from xmodule.modulestore.django import modulestore

    modulestore.side_effect = Exception("DB Error")

    test_processor = OpenEdXProcessor()
    result = test_processor.get_location_content("loc")

    assert "error" in result
    assert "DB Error" in result["error"]


# ============================================================================
# Tests: Course Outline
# ============================================================================

def test_get_course_outline(mock_edx_imports, mock_keys, processor):
    """Test full integration of getting course outline."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from lms.djangoapps.course_blocks.api import get_course_blocks
    from xmodule.modulestore.django import modulestore

    mock_store = modulestore.return_value
    mock_store.make_course_usage_key.return_value = "course-usage-key"

    mock_structure = MagicMock()
    get_course_blocks.return_value = mock_structure

    with patch.object(processor, '_serialize_block_structure_outline') as mock_serialize:
        mock_serialize.return_value = [{"title": "Test"}]

        result = processor.get_course_outline("course-v1:test", user=MagicMock())

        mock_keys[1].from_string.assert_called_with("course-v1:test")
        get_course_blocks.assert_called()
        assert result == json.dumps([{"title": "Test"}])


# ============================================================================
# Tests: Outline Serialization (Existing Parameterized Tests)
# ============================================================================

@pytest.mark.parametrize("description, children_map, fields_map, expected_structure", [
    (
        "Happy Path",
        {
            "course-root": ["chap1"], "chap1": ["seq1"], "seq1": ["vert1"], "vert1": []
        },
        {
            ("chap1", "category"): "chapter", ("chap1", "display_name"): "Sec 1",
            ("seq1", "category"): "sequential", ("seq1", "display_name"): "Sub 1",
            ("vert1", "category"): "vertical", ("vert1", "display_name"): "Unit 1"
        },
        [{"display_name": "Sec 1",
          "subsections": [{"display_name": "Sub 1", "units": [{"display_name": "Unit 1"}]}]}]
    ),
])
def test_serialize_outline_structure(processor, mock_block_structure, description, children_map, fields_map,
                                     expected_structure):
    """Verify structural correctness of serialization."""
    # pylint: disable=too-many-positional-arguments, unused-argument, protected-access
    configure_mock_bs(mock_block_structure, children_map, fields_map)
    outline = processor._serialize_block_structure_outline(mock_block_structure)
    assert len(outline) == len(expected_structure)
    if outline:
        assert outline[0]["display_name"] == expected_structure[0]["display_name"]


@pytest.mark.parametrize("scenario, children_map, fields_map", [
    ("Empty Chapter", {"course-root": ["chap1"], "chap1": []}, {("chap1", "category"): "chapter"}),
], ids=lambda x: x if isinstance(x, str) else None)
def test_serialize_outline_filtering(processor, mock_block_structure, scenario, children_map, fields_map):
    """Verify that invalid/empty blocks are filtered out."""
    # pylint: disable=unused-argument, protected-access
    configure_mock_bs(mock_block_structure, children_map, fields_map)
    assert processor._serialize_block_structure_outline(mock_block_structure) == []


def test_extract_block_delegates_to_extractor(processor):
    """
    Verify _extract_block retrieves the item and calls the matching extractor.
    """
    # pylint: disable=protected-access

    mock_store = MagicMock()
    mock_block = MagicMock()
    mock_block.category = "video"
    mock_store.get_item.return_value = mock_block

    mock_video_extractor = MagicMock(return_value={"type": "video_data"})

    module_path = "openedx_ai_extensions.processors.openedx.openedx_processor"

    with patch(f"{module_path}.COMPONENT_EXTRACTORS", {"video": mock_video_extractor}):
        result = processor._extract_block(mock_store, "block-key-123")

        mock_store.get_item.assert_called_once_with("block-key-123")
        mock_video_extractor.assert_called_once_with(mock_block)
        assert result == {"type": "video_data"}


def test_extract_block_fallback_to_generic(processor):
    """
    Verify that unknown block types fall back to extract_generic_info.
    """
    # pylint: disable=protected-access

    mock_store = MagicMock()
    mock_block = MagicMock()
    mock_block.category = "unknown_type"
    mock_store.get_item.return_value = mock_block

    module_path = "openedx_ai_extensions.processors.openedx.openedx_processor"

    with patch(f"{module_path}.extract_generic_info") as mock_generic:
        mock_generic.return_value = {"text": "generic content"}

        result = processor._extract_block(mock_store, "block-key-456")

        mock_generic.assert_called_once_with(mock_block)
        assert result == {"text": "generic content"}


def test_serialize_block_structure_full_logic(processor):
    """
    Test _serialize_block_structure_outline with a complex hierarchy to verify:
    1. Correct nesting (Section -> Subsection -> Unit).
    2. Category remapping.
    3. Filtering of empty containers.
    4. Ignoring invalid block types.
    """
    # pylint: disable=protected-access

    bs = MagicMock()
    bs.root_block_usage_key = "course-root"

    children_map = {
        "course-root": ["chapter-1", "chapter-empty", "html-root"],
        "chapter-1": ["seq-1", "seq-empty"],
        "seq-1": ["vert-1", "problem-1"],
        "seq-empty": [],
        "chapter-empty": ["html-1"],
        "vert-1": [],
    }

    fields_map = {
        ("chapter-1", "category"): "chapter", ("chapter-1", "display_name"): "Section 1",
        ("seq-1", "category"): "sequential", ("seq-1", "display_name"): "Subsection 1",
        ("vert-1", "category"): "vertical", ("vert-1", "display_name"): "Unit 1",

        ("problem-1", "category"): "problem",
        ("seq-empty", "category"): "sequential",
        ("chapter-empty", "category"): "chapter",
        ("html-1", "category"): "html",
        ("html-root", "category"): "html",
    }

    bs.get_children.side_effect = lambda key: children_map.get(key, [])
    bs.get_xblock_field.side_effect = lambda key, field: fields_map.get((key, field))

    outline = processor._serialize_block_structure_outline(bs)

    assert len(outline) == 1

    section = outline[0]
    assert section["display_name"] == "Section 1"
    assert section["category"] == "section"

    assert len(section["subsections"]) == 1

    subsection = section["subsections"][0]
    assert subsection["display_name"] == "Subsection 1"
    assert subsection["category"] == "subsection"

    assert len(subsection["units"]) == 1

    unit = subsection["units"][0]
    assert unit["display_name"] == "Unit 1"
    assert unit["category"] == "unit"


def test_process_dispatching_logic(processor):
    """
    Test that process() dynamically retrieves the function name from config
    and calls it with the provided arguments.
    """
    processor.config = {"function": "custom_method"}

    mock_method = MagicMock(return_value="success")
    processor.custom_method = mock_method

    args = (1, 2)
    kwargs = {"key": "value"}
    result = processor.process(*args, **kwargs)

    mock_method.assert_called_once_with(1, 2, key="value")
    assert result == "success"


def test_process_defaults_to_no_context(processor):
    """
    Test that process() falls back to 'no_context' method if config is missing 'function'.
    """
    processor.config = {}

    with patch.object(processor, "no_context", return_value="default_response") as mock_no_context:
        result = processor.process("arg1")

        mock_no_context.assert_called_once_with("arg1")
        assert result == "default_response"


# ============================================================================
# Tests: Course Info
# ============================================================================

def test_get_course_info_all_fields(mock_edx_imports, mock_keys):
    """Test retrieving all course info fields without outline."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from openedx.core.djangoapps.models.course_details import CourseDetails
    from xmodule.modulestore.django import modulestore

    test_processor = OpenEdXProcessor(course_id="course-v1:org+name+version")

    # Mock CourseDetails
    mock_details = MagicMock()
    mock_details.subtitle = "Test Subtitle"
    mock_details.short_description = "Short description"
    mock_details.description = "Full description"
    mock_details.overview = "<p>Overview content</p>"
    mock_details.syllabus = "Course syllabus"
    mock_details.duration = "4 weeks"
    CourseDetails.fetch.return_value = mock_details

    # Mock course block
    mock_course_block = MagicMock()
    mock_course_block.display_name = "Test Course"
    mock_store = modulestore.return_value
    mock_store.get_course.return_value = mock_course_block

    result = test_processor.get_course_info()

    assert result["title"] == "Test Course"
    assert result["subtitle"] == "Test Subtitle"
    assert result["short_description"] == "Short description"
    assert result["description"] == "Full description"
    assert result["overview"] == "<p>Overview content</p>"
    assert result["syllabus"] == "Course syllabus"
    assert result["duration"] == "4 weeks"


def test_get_course_info_specific_fields(mock_edx_imports, mock_keys):
    """Test retrieving only specific course info fields."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from openedx.core.djangoapps.models.course_details import CourseDetails
    from xmodule.modulestore.django import modulestore

    test_processor = OpenEdXProcessor(course_id="course-v1:org+name+version")

    mock_details = MagicMock()
    mock_details.subtitle = "Test Subtitle"
    mock_details.short_description = "Short description"
    CourseDetails.fetch.return_value = mock_details

    mock_course_block = MagicMock()
    mock_course_block.display_name = "Test Course"
    mock_store = modulestore.return_value
    mock_store.get_course.return_value = mock_course_block

    result = test_processor.get_course_info(fields=["title", "subtitle"])

    assert result == {"title": "Test Course", "subtitle": "Test Subtitle"}
    assert "short_description" not in result
    assert "outline" not in result


def test_get_course_info_with_outline(mock_edx_imports, mock_keys):
    """Test retrieving course info including outline."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from openedx.core.djangoapps.models.course_details import CourseDetails
    from xmodule.modulestore.django import modulestore

    test_processor = OpenEdXProcessor(course_id="course-v1:org+name+version")

    mock_details = MagicMock()
    mock_details.subtitle = ""
    CourseDetails.fetch.return_value = mock_details

    mock_course_block = MagicMock()
    mock_course_block.display_name = "Test Course"
    mock_store = modulestore.return_value
    mock_store.get_course.return_value = mock_course_block

    mock_outline = [{"display_name": "Section 1"}]

    with patch.object(test_processor, 'get_course_outline', return_value=json.dumps(mock_outline)):
        result = test_processor.get_course_info(fields=["title", "outline"])

    assert result["title"] == "Test Course"
    assert result["outline"] == json.dumps(mock_outline)
    assert "subtitle" not in result


def test_get_course_info_from_config(mock_edx_imports, mock_keys):
    """Test that fields can be specified via processor config."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from openedx.core.djangoapps.models.course_details import CourseDetails
    from xmodule.modulestore.django import modulestore

    config = {"OpenEdXProcessor": {"fields": ["title", "duration"]}}
    test_processor = OpenEdXProcessor(processor_config=config, course_id="course-v1:org+name+version")

    mock_details = MagicMock()
    mock_details.duration = "6 weeks"
    CourseDetails.fetch.return_value = mock_details

    mock_course_block = MagicMock()
    mock_course_block.display_name = "Test Course"
    mock_store = modulestore.return_value
    mock_store.get_course.return_value = mock_course_block

    result = test_processor.get_course_info()

    assert result == {"title": "Test Course", "duration": "6 weeks"}


def test_get_course_info_error_handling(mock_edx_imports, mock_keys):
    """Test that exceptions are caught and returned as errors."""
    # pylint: disable=unused-argument
    # pylint: disable=import-error, import-outside-toplevel
    from openedx.core.djangoapps.models.course_details import CourseDetails

    CourseDetails.fetch.side_effect = Exception("Database error")

    test_processor = OpenEdXProcessor(course_id="course-v1:org+name+version")
    result = test_processor.get_course_info()

    assert "error" in result
    assert "Database error" in result["error"]
