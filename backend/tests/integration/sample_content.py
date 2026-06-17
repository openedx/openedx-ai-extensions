"""
Shared sample course content for live LLM integration tests.

SAMPLE_UNIT_CONTENT mirrors the dict shape returned by
OpenEdXProcessor.get_location_content() for retrieval_mode="unit", so tests
exercise the model against the same JSON structure it receives in production
(via str(content_result) / context=content_result).
"""

WATER_CYCLE_TEXT = (
    "The water cycle describes the continuous movement of water within Earth. "
    "It has four main stages: evaporation (water turns to vapour from heat), "
    "condensation (vapour cools and forms clouds), precipitation (water falls as "
    "rain or snow), and collection (water gathers in oceans, lakes, and rivers). "
    "Energy from the sun drives the whole cycle."
)

SAMPLE_UNIT_CONTENT = {
    "unit_id": "block-v1:OpenedX+DemoX+DemoCourse+type@html+block@d4e2624ae8b3479db698413bd8947b6f",
    "display_name": "The Water Cycle",
    "category": "vertical",
    "blocks": [
        {
            "type": "html",
            "block_id": "block-v1:OpenedX+DemoX+DemoCourse+type@html+block@d4e2624ae8b3479db698413bd8947b6f",
            "title": "Introduction to the Water Cycle",
            "text": WATER_CYCLE_TEXT,
        },
    ],
}

DUMMY_CONTENT = (
    "Python is a high-level interpreted programming language created by Guido van Rossum. "
    "It emphasises code readability using significant indentation. "
    "Python supports multiple programming paradigms and has a large standard library."
)
