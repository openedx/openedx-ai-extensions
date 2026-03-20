"""
LLM Processing using LiteLLM for multiple providers
"""

import json
import logging
from pathlib import Path

from litellm import completion

from openedx_ai_extensions.processors.llm.litellm_base_processor import LitellmProcessor
from openedx_ai_extensions.processors.llm.providers import adapt_to_provider

logger = logging.getLogger(__name__)


class EducatorAssistantProcessor(LitellmProcessor):
    """Handles AI/LLM processing operations"""

    def __init__(self, user=None, context=None, **kwargs):
        super().__init__(**kwargs)
        self.context = context
        self.user = user

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        # Accept flexible arguments to match base class signature
        function_name = self.config.get("function")
        function = getattr(self, function_name)
        return function(*args, **kwargs)

    def _call_completion_api(self, system_role):
        """
        General method to call LiteLLM completion API
        Handles configuration and returns standardized response
        """
        # Build completion parameters
        completion_params = {
            "messages": [
                {"role": "system", "content": self.custom_prompt or system_role},
            ],
        }

        completion_params = adapt_to_provider(
            provider=self.provider,
            params=completion_params,
            has_user_input=False,
            user_session=self.user_session,
        )

        # Add optional parameters only if configured
        if self.extra_params:
            completion_params.update(self.extra_params)

        response = completion(**completion_params)
        content = response.choices[0].message.content

        return {
            "response": content,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "model_used": self.extra_params.get("model", "unknown"),
            "status": "success",
        }

    def generate_quiz_questions(self, input_data):
        """Generate quiz questions based on the content provided"""

        prompt_file_path = (
            Path(__file__).resolve().parent.parent.parent
            / "prompts"
            / "default_generate_quiz_questions.txt"
        )
        with open(prompt_file_path, "r") as f:
            prompt = f.read()

        input_data['context'] = self.context
        for key, value in input_data.items():
            placeholder = f"{{{{{key.upper()}}}}}"
            prompt = prompt.replace(placeholder, str(value))
        logger.info(f"Generation prompt after placeholder replacement: {prompt}")

        result = self._call_completion_api(prompt)

        tokens_used = result.get("tokens_used", 0)
        response = json.loads(result['response'])

        return {
            "response": response,
            "tokens_used": tokens_used,
            "model_used": self.extra_params.get("model", "unknown"),
            "status": "success",
        }

    def refine_quiz_question(self, input_data):
        """Refine an existing quiz question instead of generating a new one."""
        prompt_file_path = (
            Path(__file__).resolve().parent.parent.parent
            / "prompts"
            / "default_refine_quiz_question.txt"
        )
        with open(prompt_file_path, "r") as f:
            prompt = f.read()

        input_data['context'] = self.context
        for key, value in input_data.items():
            placeholder = f"{{{{{key.upper()}}}}}"
            prompt = prompt.replace(placeholder, str(value))
        logger.info(f"Refinement prompt after placeholder replacement: {prompt}")

        result = self._call_completion_api(prompt)

        tokens_used = result.get("tokens_used", 0)
        response = json.loads(result['response'])
        return {
            "response": response,
            "tokens_used": tokens_used,
            "model_used": self.extra_params.get("model", "unknown"),
            "status": "success",
        }
