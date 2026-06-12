"""
Shared json_schema response_format payloads for live LLM integration tests.

FLASHCARDS_SCHEMA is loaded directly from openedx_ai_extensions/response_schemas/
so the "additionalProperties: false" enforcement test exercises a real
production schema rather than a synthetic one.

ANSWER_SCHEMA and ARRAY_SCHEMA remain synthetic: ARRAY_SCHEMA specifically
covers the "minItems: 1" constraint, which no production response schema
currently declares.
"""

import json
from pathlib import Path

_RESPONSE_SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "openedx_ai_extensions" / "response_schemas"

with open(_RESPONSE_SCHEMAS_DIR / "flashcards.json", "r", encoding="utf-8") as _f:
    FLASHCARDS_SCHEMA = json.load(_f)

ANSWER_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
    },
}

ARRAY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "items_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    },
}
