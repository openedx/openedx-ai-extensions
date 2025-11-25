"""
Clean, LLM-friendly formatting for HTML, Video, Problem, and all other XBlocks.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def html_to_text(raw_html: str) -> str:
    """Convert HTML into clean, readable LLM-friendly text."""
    logger.debug("html_to_text: started cleaning HTML (%d chars)", len(raw_html) if raw_html else 0)

    try:
        # pylint: disable=import-error,import-outside-toplevel
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "html.parser")

        # Remove scripts & styles
        for tag in soup(["script", "style"]):
            tag.extract()

        clean = soup.get_text(separator="\n")

        # Normalize whitespace
        clean = "\n".join(
            line.strip() for line in clean.splitlines() if line.strip()
        )

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


def extract_generic_info(block) -> dict:
    """Catch-all extractor for unknown block types with clean formatting."""
    logger.debug("extract_generic_info: processing %s", block.location)

    safe_fields = {}
    for field in getattr(block, "fields", []):
        value = getattr(block, field, None)
        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
            safe_fields[field] = value

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
