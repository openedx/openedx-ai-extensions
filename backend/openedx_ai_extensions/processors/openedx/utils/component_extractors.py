"""
Clean, LLM-friendly formatting for HTML, Video, Problem, and all other XBlocks.
"""

import json
import logging
from typing import Optional

from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_field_filters():
    """Return field filters from settings, accessed lazily to avoid import-time errors."""
    return getattr(settings, "AI_EXTENSIONS_FIELD_FILTERS", {})


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
            embeddings.append(f'[Embedded iframe: title="{title}", src="{src}"]')
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
                embeddings.append(f'[Embedded PDF: title="{title}", file="{data}"]')
            else:
                embeddings.append(
                    f'[Embedded object: title="{title}", type="{mime}", file="{data}"]'
                )
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
            embeddings.append(f'[Embedded image: alt="{alt}", src="{src}"]')
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
            embeddings.append(
                f'[Embedded {media.name}: title="{title}", sources="{sources_str}"]'
            )
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
            embeddings.append(f'[Embedded content: tag=embed, src="{src}"]')
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
                desc += f': type="{xblock_type}"'
            if block_id:
                desc += f', id="{block_id}"'
            desc += "]"
            embeddings.append(desc)
    return embeddings


def _check_show_answer(show_answer):
    """
    Basic show-answer check.

    NOTE:
        This is a simplified implementation. Currently it only returns True
        when `showanswer` is set to "always".

        This function can be extended to apply more intelligent logic based on:
            - the block's `showanswer` policy,
            - the student's attempts,
            - correctness,
            - past-due dates,
            - max_attempts,
            - and overall StudentModule state.

        For now, it remains intentionally minimal.
    """
    return show_answer == "always"


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def html_to_text(raw_html: str) -> str:
    """
    Convert HTML into clean, LLM-friendly text, preserving embedded content info.
    """
    logger.debug(
        "html_to_text: started cleaning HTML (%d chars)",
        len(raw_html) if raw_html else 0,
    )
    try:
        soup = BeautifulSoup(raw_html, "html.parser")

        embeddings = []
        embeddings.extend(_extract_iframes(soup))
        embeddings.extend(_extract_objects(soup))
        embeddings.extend(_extract_images(soup))
        embeddings.extend(_extract_media(soup))
        embeddings.extend(_extract_embeds(soup))
        embeddings.extend(_extract_xblocks(soup))

        # Remove noisy tags after extraction
        _clean_noisy_tags(soup)

        clean = "\n".join(
            line.strip()
            for line in soup.get_text(separator="\n").splitlines()
            if line.strip()
        )

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
        logger.debug(
            "_load_transcript_content: fetching transcript via edxval for video %s",
            edx_video_id,
        )

        transcript = get_video_transcript_data(
            video_id=edx_video_id, language_code=language_code
        )

        content = transcript["content"]
        if isinstance(content, bytes):
            content = content.decode("utf-8")
            logger.debug("_load_transcript_content: decoded bytes content")

        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "_load_transcript_content: transcript content is not valid JSON, returning raw content"
            )

        logger.debug("_load_transcript_content: transcript content successfully loaded")
        return content.get("text") if isinstance(content, dict) else content

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("_load_transcript_content: failed to load transcript: %s", exc)
        return transcripts


def _remove_sensitive_content(soup: BeautifulSoup):
    """Remove hints, solutions, and correctness info when show_answer=False."""
    sensitive_tags = ["choicehint", "solution", "demandhint", "hint"]
    sensitive_selectors = [
        ".solution-span",
        ".detailed-solution",
        ".feedback-hint",
        ".notification-submit",
        ".status",
        ".correctness",
    ]
    for tag_name in sensitive_tags:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    for selector in sensitive_selectors:
        for tag in soup.select(selector):
            tag.decompose()
    for choice in soup.find_all("choice"):
        if choice.has_attr("correct"):
            del choice["correct"]


def _extract_solution_feedback(soup: BeautifulSoup) -> list[str]:
    """Extract solutions, hints, and feedback when show_answer=True."""
    extracted_sections = []

    # Mark correct answers
    for choice in soup.find_all("choice", attrs={"correct": "true"}):
        choice.insert(0, soup.new_string("[CORRECT ANSWER] "))

    def _pull(tag_name, label):
        for tag in soup.find_all(tag_name):
            text = tag.get_text(" ", strip=True)
            if text:
                extracted_sections.append(f"[{label}]: {text}")
            tag.decompose()

    _pull("choicehint", "Feedback")
    _pull("hint", "Hint")
    _pull("demandhint", "Hint")
    _pull("solution", "Solution")

    sensitive_selectors = [
        ".solution-span",
        ".detailed-solution",
        ".feedback-hint",
        ".notification-submit",
        ".status",
        ".correctness",
    ]
    for selector in sensitive_selectors:
        for tag in soup.select(selector):
            text = tag.get_text(" ", strip=True)
            if text:
                extracted_sections.append(f"[Feedback/Explanation]: {text}")
            tag.decompose()

    return extracted_sections


def _clean_noisy_tags(soup: BeautifulSoup):
    """
    Remove noisy HTML tags that are not useful for LLM text extraction.
    """
    noisy_tags = [
        "script",
        "style",
        "iframe",
        "embed",
        "object",
        "video",
        "audio",
        "img",
    ]
    for tag in soup.find_all(noisy_tags):
        tag.extract()


def _assemble_problem_text(
    soup: BeautifulSoup, extracted_sections: list[str], show_answer: bool
) -> str:
    """Assemble clean text and append solution/feedback if show_answer=True."""
    base_text = "\n".join(
        line.strip()
        for line in soup.get_text(separator="\n").splitlines()
        if line.strip()
    )
    if show_answer and extracted_sections:
        base_text += "\n" + "\n".join(extracted_sections)
    return base_text


def _process_problem_html(raw_html: str, show_answer: bool) -> str:
    """Main entry point for processing problem HTML."""
    if not raw_html:
        return ""

    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        extracted_sections = []

        if show_answer:
            extracted_sections = _extract_solution_feedback(soup)
        else:
            _remove_sensitive_content(soup)

        _clean_noisy_tags(soup)
        return _assemble_problem_text(soup, extracted_sections, show_answer)

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(f"Error processing problem HTML: {exc}")
        return raw_html


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
        logger.debug(
            "extract_video_info: transcript found (%d chars)", len(str(transcript_text))
        )
        info["transcript_text"] = transcript_text
    else:
        logger.info(
            "extract_video_info: no transcript available for block %s", block.location
        )

    return info


def extract_html_info(block) -> dict:
    """Return cleaned HTML block content as plain text with metadata."""
    logger.debug("extract_html_info: processing block %s", block.location)
    raw_html = getattr(block, "data", "") or ""
    text = html_to_text(raw_html)
    return {
        "type": "html",
        "block_id": str(block.location),
        "title": block.display_name,
        "text": text,
    }


def extract_problem_info(block, show_answer) -> dict:
    """Return processed problem content, optionally including answers/hints."""
    logger.debug("extract_problem_info: processing %s", block.location)
    raw = getattr(block, "data", "") or ""

    if show_answer == "auto":
        show_answer = _check_show_answer(getattr(block, "showanswer", False))

    text = _process_problem_html(raw, show_answer)
    return {
        "type": "problem",
        "block_id": str(block.location),
        "title": block.display_name,
        "text": text,
    }


def extract_discussion_info(block) -> dict:
    """Return discussion block metadata (IDs, category, target)."""
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
    filters = _get_field_filters()
    allowed_fields = filters.get("allowed_fields", [])
    allowed_field_substrings = filters.get("allowed_field_substrings", [])
    fname = field_name.lower()

    # 1. Exact allow-list
    if fname in allowed_fields:
        return True

    # 2. Substring allow-list
    for substring in allowed_field_substrings:
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
            logger.debug(
                "extract_generic_info: excluded field '%s' (not allowed)", field
            )
            continue

        value = getattr(block, field, None)

        # Only safe primitive-like values are included
        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
            safe_fields[field] = value
        else:
            logger.debug(
                "extract_generic_info: excluded field '%s' (unsupported type %s)",
                field,
                type(value),
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
