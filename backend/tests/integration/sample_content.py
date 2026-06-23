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

SHORT_CONTENT = "Python uses indentation to define code blocks."

LONG_SYSTEM_CONTEXT = (
    "The history of computing spans several decades. "
    "From vacuum tubes to transistors to integrated circuits, each era "
    "brought dramatic improvements in speed, size, and cost. "
    "ENIAC (1945) was the first general-purpose electronic computer, "
    "weighing 30 tons and occupying an entire room. "
    "The invention of the transistor in 1947 at Bell Labs was a watershed moment, "
    "enabling miniaturisation that made personal computers possible. "
    "Intel released the first commercial microprocessor, the 4004, in 1971. "
    "The IBM PC in 1981 standardised the personal computer market. "
    "Tim Berners-Lee invented the World Wide Web in 1989, transforming computing. "
    "The rise of smartphones in the 2000s put computing in every pocket. "
    "Cloud computing emerged in the 2010s, shifting workloads to remote data centres. "
    "Today artificial intelligence, driven by GPUs and large language models, "
    "represents the next major inflection point in the history of computing technology. "
) * 24  # Repeat to exceed Anthropic's cache minimum (4096 tokens for claude-haiku-4-5)
