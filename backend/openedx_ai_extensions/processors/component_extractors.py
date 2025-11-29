"""
Clean, LLM-friendly formatting for HTML, Video, Problem, and all other XBlocks.
"""

import json
import logging
from typing import Optional

from bs4 import BeautifulSoup  # pylint: disable=import-error
from django.conf import settings

logger = logging.getLogger(__name__)

filters = settings.AI_EXTENSIONS_FIELD_FILTERS
ALLOWED_FIELDS = filters.get("allowed_fields", [])
ALLOWED_FIELD_SUBSTRINGS = filters.get("allowed_field_substrings", [])
# -----------------------------
# Embedded content helpers
# -----------------------------


def _extract_iframes(soup: BeautifulSoup) -> list[str]:
    """
    Extract all <iframe> tags from the HTML and return
    a list of LLM-friendly strings describing the embedded iframes.

    Example output:
    '[Embedded iframe: title="Video Player", src="/path/to/video"]'
    """
    embeddings = []
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        title = iframe.get("title", "").strip() or "iframe"
        if src:
            embeddings.append(f"[Embedded iframe: title=\"{title}\", src=\"{src}\"]")
    return embeddings


def _extract_objects(soup: BeautifulSoup) -> list[str]:
    """
    Extract <object> tags, identifying PDFs and other objects.
    Returns a list of strings describing each embedded object.

    Example output:
    '[Embedded PDF: title="Manual", file="/static/manual.pdf"]'
    '[Embedded object: title="3D Model", type="application/x-3d", file="/assets/model.obj"]'
    """
    embeddings = []
    for obj in soup.find_all("object"):
        data = obj.get("data")
        mime = obj.get("type", "")
        title = obj.get("title", "").strip() or "Object"
        if data:
            if "pdf" in mime.lower() or data.lower().endswith(".pdf"):
                embeddings.append(f"[Embedded PDF: title=\"{title}\", file=\"{data}\"]")
            else:
                embeddings.append(f"[Embedded object: title=\"{title}\", type=\"{mime}\", file=\"{data}\"]")
    return embeddings


def _extract_images(soup: BeautifulSoup) -> list[str]:
    """
    Extract <img> tags and return a list of strings describing the images.

    Example output:
    '[Embedded image: alt="Logo", src="/static/logo.png"]'
    """
    embeddings = []
    for img in soup.find_all("img"):
        src = img.get("src")
        alt = img.get("alt", "").strip() or "image"
        if src:
            embeddings.append(f"[Embedded image: alt=\"{alt}\", src=\"{src}\"]")
    return embeddings


def _extract_media(soup: BeautifulSoup) -> list[str]:
    """
    Extract <video> and <audio> tags, including <source> elements.
    Returns a list of descriptive strings.

    Example output:
    '[Embedded video: title="Lecture", sources="/videos/lec.mp4, /videos/lec.webm"]'
    """
    embeddings = []
    for media in soup.find_all(["video", "audio"]):
        sources = [s.get("src") for s in media.find_all("source") if s.get("src")]
        direct_src = media.get("src")
        if direct_src and direct_src not in sources:
            sources.append(direct_src)

        title = media.get("title", "").strip() or media.name
        if sources:
            sources_str = ", ".join(sources)
            embeddings.append(f"[Embedded {media.name}: title=\"{title}\", sources=\"{sources_str}\"]")
    return embeddings


def _extract_embeds(soup: BeautifulSoup) -> list[str]:
    """
    Extract <embed> tags and return descriptive strings.

    Example output:
    '[Embedded content: tag=embed, src="/assets/interactive.swf"]'
    """
    embeddings = []
    for embed in soup.find_all("embed"):
        src = embed.get("src")
        if src:
            embeddings.append(f"[Embedded content: tag=embed, src=\"{src}\"]")
    return embeddings


def _extract_xblocks(soup: BeautifulSoup) -> list[str]:
    """
    Extract custom XBlock placeholders from <div> tags with data-type or data-block-id.
    Returns descriptive strings for LLM consumption.

    Example output:
    '[Embedded XBlock: type="problem", id="block-v1:course+unit+block"]'
    """
    embeddings = []
    for div in soup.find_all("div"):
        xblock_type = div.get("data-type")
        block_id = div.get("data-block-id")
        if xblock_type or block_id:
            desc = "[Embedded XBlock"
            if xblock_type:
                desc += f": type=\"{xblock_type}\""
            if block_id:
                desc += f", id=\"{block_id}\""
            desc += "]"
            embeddings.append(desc)
    return embeddings


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def html_to_text(raw_html: str) -> str:
    """
    Convert HTML into clean, LLM-friendly text, preserving embedded content info.
    """
    logger.debug("html_to_text: started cleaning HTML (%d chars)", len(raw_html) if raw_html else 0)
    try:
        soup = BeautifulSoup(raw_html, "html.parser")

        embeddings = []
        embeddings.extend(_extract_iframes(soup))
        embeddings.extend(_extract_objects(soup))
        embeddings.extend(_extract_images(soup))
        embeddings.extend(_extract_media(soup))
        embeddings.extend(_extract_embeds(soup))
        embeddings.extend(_extract_xblocks(soup))

        # Remove embedded tags after extraction
        for tag in soup.find_all(["iframe", "object", "img", "video", "audio", "embed"]):
            tag.extract()

        # Remove scripts & styles
        for tag in soup(["script", "style"]):
            tag.extract()

        clean = "\n".join(line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip())

        if embeddings:
            clean += "\n\n" + "\n".join(embeddings)

        logger.debug("html_to_text: finished cleaning HTML (%d chars)", len(clean))
        return clean.strip()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("html_to_text: failed to clean HTML: %s", exc)
        return raw_html  # fallback


def _load_transcript_content(block) -> Optional[dict]:
    """
    Returns transcript content as clean text.
    """
    logger.debug("_load_transcript_content: loading transcript for block %s", block)

    transcripts = getattr(block, "transcripts", {}) or {}
    if not transcripts:
        logger.info("_load_transcript_content: no transcripts found")
        return None

    # prefer english, fallback to next available
    language_code = "en" if "en" in transcripts else next(iter(transcripts.keys()))
    logger.debug("_load_transcript_content: selected language '%s'", language_code)

    # use edxval API
    try:
        # pylint: disable=import-error,import-outside-toplevel
        from edxval.api import get_video_transcript_data

        edx_video_id = getattr(block, "edx_video_id", None)
        logger.debug("_load_transcript_content: fetching transcript via edxval for video %s", edx_video_id)

        transcript = get_video_transcript_data(video_id=edx_video_id, language_code=language_code)

        content = transcript["content"]
        if isinstance(content, bytes):
            content = content.decode("utf-8")
            logger.debug("_load_transcript_content: decoded bytes content")

        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("_load_transcript_content: transcript content is not valid JSON, returning raw content")

        logger.debug("_load_transcript_content: transcript content successfully loaded")
        return content.get("text") if isinstance(content, dict) else content

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("_load_transcript_content: failed to load transcript: %s", exc)
        return transcripts


# ---------------------------------------------------------
# Block Extractors
# ---------------------------------------------------------

def extract_video_info(block) -> dict:
    """Extract rich metadata for video blocks, including transcripts."""
    logger.debug("extract_video_info: extracting video block %s", block.location)

    info = {
        "type": "video",
        "block_id": str(block.location),
        "title": block.display_name,
        "edx_video_id": getattr(block, "edx_video_id", None),
        "youtube_id": getattr(block, "youtube_id_1_0", None),
    }

    transcript_text = _load_transcript_content(block)
    if transcript_text:
        logger.debug("extract_video_info: transcript found (%d chars)", len(str(transcript_text)))
        info["transcript_text"] = transcript_text
    else:
        logger.info("extract_video_info: no transcript available for block %s", block.location)

    return info


def extract_html_info(block) -> dict:
    logger.debug("extract_html_info: processing block %s", block.location)
    raw_html = getattr(block, "data", "") or ""
    text = html_to_text(raw_html)
    return {
        "type": "html",
        "block_id": str(block.location),
        "title": block.display_name,
        "text": text,
    }


def extract_problem_info(block) -> dict:
    logger.debug("extract_problem_info: processing %s", block.location)
    raw = getattr(block, "data", "") or ""
    text = html_to_text(raw)
    return {
        "type": "problem",
        "block_id": str(block.location),
        "title": block.display_name,
        "text": text,
    }


def extract_discussion_info(block) -> dict:
    logger.debug("extract_discussion_info: processing %s", block.location)
    return {
        "type": "discussion",
        "block_id": str(block.location),
        "title": block.display_name,
        "discussion_id": getattr(block, "discussion_id", None),
        "category": getattr(block, "discussion_category", None),
        "target": getattr(block, "discussion_target", None),
    }


def _is_field_allowed(field_name: str) -> bool:
    """
    Returns True if field_name is explicitly allowed or matches an allowed substring.
    """
    fname = field_name.lower()

    # 1. Exact allow-list
    if fname in ALLOWED_FIELDS:
        return True

    # 2. Substring allow-list
    for substring in ALLOWED_FIELD_SUBSTRINGS:
        if substring in fname:
            return True

    return False


def extract_generic_info(block) -> dict:
    """
    Catch-all extractor for unknown block types with allow-list filtering.
    Only fields explicitly allowed or matching allowed substrings are included.
    """
    logger.debug("extract_generic_info: processing %s", block.location)

    safe_fields = {}
    for field in getattr(block, "fields", []):
        if not _is_field_allowed(field):
            logger.debug("extract_generic_info: excluded field '%s' (not allowed)", field)
            continue

        value = getattr(block, field, None)

        # Only safe primitive-like values are included
        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
            safe_fields[field] = value
        else:
            logger.debug(
                "extract_generic_info: excluded field '%s' (unsupported type %s)",
                field,
                type(value)
            )

    return {
        "type": getattr(block, "category", "unknown"),
        "block_id": str(block.location),
        "title": block.display_name,
        "fields": safe_fields,
    }


COMPONENT_EXTRACTORS = {
    "html": extract_html_info,
    "problem": extract_problem_info,
    "video": extract_video_info,
    "discussion": extract_discussion_info,
}
