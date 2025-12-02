"""
LLM Processing using LiteLLM for multiple providers
"""

import json
import logging
import os

from django.conf import settings
from litellm import completion

logger = logging.getLogger(__name__)


class EducatorAssistantProcessor:
    """Handles AI/LLM processing operations"""

    def __init__(self, config=None, user=None, context=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})
        self.user = user
        self.context = context

        self.config_profile = self.config.get("config", "default")

        # Extract API configuration once during initialization
        self.api_key = settings.AI_EXTENSIONS[self.config_profile]['API_KEY']
        self.model = settings.AI_EXTENSIONS[self.config_profile]['LITELLM_MODEL']

        self.extra_params = {}
        if hasattr(settings.AI_EXTENSIONS[self.config_profile], 'TIMEOUT'):
            self.extra_params['timeout'] = settings.AI_EXTENSIONS[self.config_profile]['TIMEOUT']
        if hasattr(settings.AI_EXTENSIONS[self.config_profile], 'TEMPERATURE'):
            self.extra_params['temperature'] = settings.AI_EXTENSIONS[self.config_profile]['TEMPERATURE']
        if hasattr(settings.AI_EXTENSIONS[self.config_profile], 'MAX_TOKENS'):
            self.extra_params['max_tokens'] = settings.AI_EXTENSIONS[self.config_profile]['MAX_TOKENS']

        if not self.api_key:
            logger.error("AI API key not configured")

    def process(self, input_data):
        """Process based on configured function"""
        function_name = self.config.get("function")
        function = getattr(self, function_name)
        return function(input_data)

    def _call_completion_api(self, system_role):
        """
        General method to call LiteLLM completion API
        Handles configuration and returns standardized response
        """
        try:
            if not self.api_key:
                return {"error": "AI API key not configured"}

            # Build completion parameters
            completion_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_role},
                ],
                "api_key": self.api_key,
            }

            # Add optional parameters only if configured
            if self.extra_params:
                completion_params.update(self.extra_params)

            response = completion(**completion_params)
            content = response.choices[0].message.content

            return {
                "response": content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.model,
                "status": "success",
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

    def generate_quiz_questions(self, input_data):
        """Generate quiz questions based on the content provided"""
        requested_questions = input_data.get('num_questions')
        extra_instructions = input_data.get('extra_instructions')

        prompt_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'prompts',
            'default_generate_quiz_questions.txt'
        )
        try:
            with open(prompt_file_path, "r") as f:
                prompt = f.read()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error loading prompt template: {e}")
            return {"error": "Failed to load prompt template."}

        if '{{NUM_QUESTIONS}}' in prompt:
            prompt = prompt.replace("{{NUM_QUESTIONS}}", str(requested_questions))
        if '{{CONTEXT}}' in prompt:
            prompt = prompt.replace("{{CONTEXT}}", str(self.context))
        if '{{EXTRA_INSTRUCTIONS}}' in prompt:
            prompt = prompt.replace("{{EXTRA_INSTRUCTIONS}}", extra_instructions or "")

        result = self._call_completion_api(prompt)
        tokens_used = result.get("tokens_used", 0)

        # if response is not json serializable, try 3 times to fix it
        response = []
        for attempt in range(3):
            try:
                response = json.loads(result['response'])
                break
            except json.JSONDecodeError:
                result = self._call_completion_api(prompt)
                tokens_used += result.get("tokens_used", 0)
                if attempt == 2:
                    return {
                        "error": "Failed to parse AI response as JSON after multiple attempts.",
                        "tokens_used": tokens_used,
                        "model_used": self.model,
                    }

        return {
            "response": response,
            "tokens_used": tokens_used,
            "model_used": self.model,
            "status": "success",
        }
