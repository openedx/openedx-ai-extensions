"""
AIExtensionsXBlockService — façade that exposes AI Extensions to XBlocks
via the standard XBlock services mechanism.

XBlocks should not import any symbol from this module directly.  They
should declare ``@XBlock.wants("ai_extensions")`` and obtain the service
through ``self.runtime.service(self, "ai_extensions")``.
"""

import logging

logger = logging.getLogger(__name__)


class AIExtensionsXBlockService:
    """XBlock service façade for the AI Extensions framework."""

    def __init__(self, user, course_id=None, location_id=None):
        self._user = user
        self._course_id = course_id
        self._location_id = location_id

    def call_llm(
        self,
        prompt,
        context=None,
        user_input=None,
        extra_params=None,
    ):
        """
        Make a single, stateless LLM call via ``LLMProcessor``.

        Args:
            prompt (str): System / instruction prompt for the LLM.
            context (str | None): Additional context injected alongside the
                prompt (e.g. course content, block transcript).
            user_input (str | None): The user-facing input text.
            extra_params (dict | None): Extra ``LiteLLM`` parameters such as
                ``model``, ``temperature``, or ``max_tokens``.  Passed
                directly to ``LLMProcessor``.

        Returns:
            dict: ``{response, tokens_used, model_used, status}`` on
            success, or ``{status: "error", error: "..."}`` on failure.
        """
        from openedx_ai_extensions.processors import LLMProcessor  # pylint: disable=import-outside-toplevel

        config = {
            "LLMProcessor": {
                "function": "call_with_custom_prompt",
                "prompt": prompt or "Answer the question.",
                "provider": "openai",
            }
        }

        try:
            processor = LLMProcessor(config=config, extra_params=extra_params or {})
            return processor.process(context=context, input_data=user_input)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("ai_extensions XBlock service: call_llm failed: %s", exc)
            return {"status": "error", "error": str(exc)}
