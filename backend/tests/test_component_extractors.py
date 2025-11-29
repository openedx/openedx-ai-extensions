"""
Unit tests for component_extractors module.

These tests cover HTML extraction helpers, html_to_text conversion, transcript loading,
block extractors, and allowed field filtering. Mocks are used for edxval API interactions.
"""

import json
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from django.conf import settings

from openedx_ai_extensions.processors.component_extractors import (
    _extract_embeds,
    _extract_iframes,
    _extract_images,
    _extract_media,
    _extract_objects,
    _extract_xblocks,
    _is_field_allowed,
    _load_transcript_content,
    extract_discussion_info,
    extract_generic_info,
    extract_html_info,
    extract_problem_info,
    extract_video_info,
    html_to_text,
)

# -------------------------------------------------------------------------
# HTML EXTRACTION HELPERS
# -------------------------------------------------------------------------


def test_extract_iframes():
    """Test that <iframe> tags are converted into LLM-friendly descriptive strings."""
    soup = BeautifulSoup('<iframe src="/x" title="Player"></iframe>', "html.parser")
    result = _extract_iframes(soup)
    assert result == ['[Embedded iframe: title="Player", src="/x"]']


def test_extract_objects_pdf():
    """Test that <object> tags with PDF MIME type are correctly identified as PDFs."""
    soup = BeautifulSoup(
        '<object data="/a.pdf" type="application/pdf" title="Doc"></object>', "html.parser"
    )
    assert _extract_objects(soup) == ['[Embedded PDF: title="Doc", file="/a.pdf"]']


def test_extract_objects_generic():
    """Test extraction of non-PDF <object> tags."""
    soup = BeautifulSoup('<object data="/a.obj" type="3d/obj"></object>', "html.parser")
    assert _extract_objects(soup) == ['[Embedded object: title="Object", type="3d/obj", file="/a.obj"]']


def test_extract_images():
    """Test that <img> tags are converted into descriptive strings with alt and src."""
    soup = BeautifulSoup('<img src="/img.png" alt="Logo">', "html.parser")
    assert _extract_images(soup) == ['[Embedded image: alt="Logo", src="/img.png"]']


def test_extract_media():
    """Test extraction of <video> and <audio> tags including <source> elements."""
    soup = BeautifulSoup(
        '<video title="Lec"><source src="/v1.mp4"><source src="/v2.webm"></video>',
        "html.parser",
    )
    assert _extract_media(soup) == [
        '[Embedded video: title="Lec", sources="/v1.mp4, /v2.webm"]'
    ]


def test_extract_embeds():
    """Test extraction of <embed> tags into descriptive strings."""
    soup = BeautifulSoup('<embed src="/x.swf">', "html.parser")
    assert _extract_embeds(soup) == ['[Embedded content: tag=embed, src="/x.swf"]']


def test_extract_xblocks():
    """Test extraction of custom XBlock <div> placeholders."""
    soup = BeautifulSoup('<div data-type="problem" data-block-id="id123"></div>', "html.parser")
    assert _extract_xblocks(soup) == ['[Embedded XBlock: type="problem", id="id123"]']


# -------------------------------------------------------------------------
# html_to_text
# -------------------------------------------------------------------------

def test_html_to_text_basic():
    """Test html_to_text converts HTML paragraphs into clean text lines."""
    result = html_to_text("<p>Hello <b>world</b></p>")
    assert result == "Hello\nworld"


def test_html_to_text_with_embeds():
    """Test html_to_text extracts embeds, removes tags, and appends metadata."""
    html = '<p>A</p><iframe src="/x" title="Player"></iframe>'
    result = html_to_text(html)
    assert "A" in result
    assert "Embedded iframe" in result
    assert "<iframe" not in result


def test_html_to_text_invalid_html():
    """Test html_to_text returns raw HTML if parsing fails."""
    with patch("openedx_ai_extensions.processors.component_extractors.BeautifulSoup", side_effect=Exception):
        assert html_to_text("<bad>") == "<bad>"


# -------------------------------------------------------------------------
# Transcript Loading
# -------------------------------------------------------------------------

def test_load_transcript_prefers_english_sys_modules():
    """Test that English transcripts are preferred using sys.modules patch."""
    block = MagicMock()
    block.transcripts = {"en": {"text": "Hello"}, "fr": {"text": "Bonjour"}}
    block.edx_video_id = "vid1"

    mock_get_video_transcript_data = MagicMock(return_value={"content": json.dumps({"text": "Hello"})})
    mock_edxval_api = MagicMock()
    mock_edxval_api.get_video_transcript_data = mock_get_video_transcript_data

    with patch.dict("sys.modules", {"edxval.api": mock_edxval_api}):
        result = _load_transcript_content(block)
        assert result == "Hello"
        mock_get_video_transcript_data.assert_called_once_with(video_id="vid1", language_code="en")


def test_load_transcript_bytes_content():
    """Test that transcript loader decodes byte content correctly."""
    block = MagicMock()
    block.transcripts = {"en": {}}
    block.edx_video_id = "vid1"

    mock_get_video_transcript_data = MagicMock(
        return_value={"content": json.dumps({"text": "bytes content"}).encode("utf-8")}
    )
    mock_edxval_api = MagicMock()
    mock_edxval_api.get_video_transcript_data = mock_get_video_transcript_data

    with patch.dict("sys.modules", {"edxval.api": mock_edxval_api}):
        result = _load_transcript_content(block)
        assert result == "bytes content"


def test_load_transcript_invalid_json_returns_raw():
    """Test that invalid JSON content returns raw string."""
    block = MagicMock()
    block.transcripts = {"en": {}}
    block.edx_video_id = "v1"

    mock_get_video_transcript_data = MagicMock(return_value={"content": "not-json"})
    mock_edxval_api = MagicMock()
    mock_edxval_api.get_video_transcript_data = mock_get_video_transcript_data

    with patch.dict("sys.modules", {"edxval.api": mock_edxval_api}):
        result = _load_transcript_content(block)
        assert result == "not-json"


def test_load_transcript_no_transcripts():
    """Test loader returns None if no transcripts are present."""
    block = MagicMock()
    block.transcripts = {}
    assert _load_transcript_content(block) is None


def test_load_transcript_api_error_fallback():
    """Test that API exceptions return the original transcripts dict."""
    block = MagicMock()
    block.transcripts = {"en": {"text": "fallback"}}
    block.edx_video_id = "v1"

    mock_get_video_transcript_data = MagicMock(side_effect=Exception("fail"))
    mock_edxval_api = MagicMock()
    mock_edxval_api.get_video_transcript_data = mock_get_video_transcript_data

    with patch.dict("sys.modules", {"edxval.api": mock_edxval_api}):
        result = _load_transcript_content(block)
        assert result == block.transcripts


# -------------------------------------------------------------------------
# Block extractors
# -------------------------------------------------------------------------

def make_block(category="html", **fields):
    """Helper to create a pseudo-block object with given fields."""
    block = MagicMock()
    for k, v in fields.items():
        setattr(block, k, v)
    block.category = category
    block.location = "loc123"
    return block


def test_extract_html_info():
    """Test extraction of HTML blocks returns cleaned text."""
    block = make_block(data="<p>Hi</p>", display_name="HTML Block")
    result = extract_html_info(block)
    assert result["type"] == "html"
    assert "Hi" in result["text"]


def test_extract_problem_info():
    """Test extraction of Problem blocks uses html_to_text."""
    block = make_block(category="problem", data="<p>Q?</p>", display_name="Prob")
    result = extract_problem_info(block)
    assert result["type"] == "problem"
    assert "Q?" in result["text"]


def test_extract_discussion_info():
    """Test extraction of Discussion blocks returns relevant discussion fields."""
    block = make_block(
        category="discussion",
        display_name="Discuss",
        discussion_id="d1",
        discussion_category="cat",
        discussion_target="tgt"
    )
    result = extract_discussion_info(block)
    assert result["discussion_id"] == "d1"
    assert result["title"] == "Discuss"


def test_extract_video_info_with_transcript():
    """Test extraction of Video blocks includes transcript if available."""
    block = make_block(category="video", display_name="Vid", edx_video_id="v1")
    block.transcripts = {"en": {}}
    result = extract_video_info(block)
    assert result["type"] == "video"
    assert "transcript_text" in result


def test_extract_video_info_no_transcript():
    """Test extraction of Video blocks omits transcript_text when none exists."""
    block = make_block(category="video", display_name="Vid")
    block.transcripts = {}
    result = extract_video_info(block)
    assert "transcript_text" not in result


# -------------------------------------------------------------------------
# Allowed field filtering
# -------------------------------------------------------------------------

def test_is_field_allowed(monkeypatch):
    """Test that exact and substring allowed fields are correctly identified."""
    monkeypatch.setattr(
        settings,
        "AI_EXTENSIONS_FIELD_FILTERS",
        {"allowed_fields": ["title", "level"], "allowed_field_substrings": ["desc"]}
    )
    assert _is_field_allowed("title")
    assert _is_field_allowed("short_description")
    assert not _is_field_allowed("other")


def test_extract_generic_info_filters_fields(monkeypatch):
    """Test extract_generic_info only returns allowed primitive fields."""
    monkeypatch.setattr(
        settings,
        "AI_EXTENSIONS_FIELD_FILTERS",
        {"allowed_fields": ["title"]}
    )
    block = make_block(
        category="other",
        display_name="Block",
        fields=["title", "metadata", "skip_me"],
        title="OK",
        metadata={"a": 1},
        skip_me=object()
    )
    result = extract_generic_info(block)["fields"]
    assert "title" in result
    assert "skip_me" not in result
