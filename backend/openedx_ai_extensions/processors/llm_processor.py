"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from django.conf import settings
from litellm import completion
from .library_utils import create_container, create_block, modify_block_olx, publish_changes
from uuid import uuid4

logger = logging.getLogger(__name__)


class LLMProcessor:
    """Handles AI/LLM processing operations"""

    def __init__(self, config=None, user=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})
        self.user = user

        self.config_profile = self.config.get("config", "default")

        # Extract API configuration once during initialization
        self.api_key = settings.AI_EXTENSIONS[self.config_profile]['API_KEY']
        self.model = settings.AI_EXTENSIONS[self.config_profile]['LITELLM_MODEL']
        self.timeout = settings.AI_EXTENSIONS[self.config_profile]['TIMEOUT']
        self.temperature = settings.AI_EXTENSIONS[self.config_profile]['TEMPERATURE']
        self.max_tokens = settings.AI_EXTENSIONS[self.config_profile]['MAX_TOKENS']

        if not self.api_key:
            logger.error("AI API key not configured")

    def process(self, input_data):
        """Process based on configured function"""
        function_name = self.config.get("function", "summarize_content")
        function = getattr(self, function_name)
        return function(input_data)

    def _call_completion_api(self, system_role, user_content):
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
                    {"role": "user", "content": user_content},
                ],
                "api_key": self.api_key,
            }

            # Add optional parameters only if configured
            if self.temperature is not None:
                completion_params["temperature"] = self.temperature
            if self.max_tokens is not None:
                completion_params["max_tokens"] = self.max_tokens
            if self.timeout is not None:
                completion_params["timeout"] = self.timeout

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

    def summarize_content(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Summarize content using LiteLLM"""
        system_role = (
            "You are an academic assistant which helps students briefly "
            "summarize a unit of content of an online course."
        )

        result = self._call_completion_api(system_role, content_text)

        return result

    def explain_like_five(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """
        Explain content in very simple terms, like explaining to a 5-year-old
        Short, simple language that anyone can understand
        """
        system_role = (
            "You are a friendly teacher who explains things to young children. "
            "Explain the content in very simple words, like you're talking to a 5-year-old. "
            "Use short sentences, simple words, and make it fun and easy to understand. "
            "Keep your explanation very brief - no more than 3-4 simple sentences."
        )

        result = self._call_completion_api(system_role, content_text)

        return result

    def openai_hello(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Simple test function to call OpenAI API via LiteLLM"""

        lib_name = "demo1:demo1"
        lib_key_str = f"lib:{lib_name}"
        # data = {
        #     "container_type": "unit",
        #     "display_name": "Test Library Unit from LLM"
        # }
        # unit = create_container(lib_key_str, self.user, data)
        # logger.info(f"TEST Created library container: {unit}")

        block_data = {
          "block_type": "problem",
          "definition_id": str(uuid4()),
          "can_stand_alone": True,
        }
        problem = create_block(lib_key_str, self.user, block_data)
        logger.info(f"TEST Created library block: {problem}")

        problem_data = {
          "category": "problem",
          "courseKey": lib_key_str,
          "data": "<problem><choiceresponse>\n<div>question2</div><checkboxgroup><choice correct=\"true\"><div>1</div></choice><choice correct=\"false\"><div>2</div></choice><choice correct=\"false\"><div>3</div></choice></checkboxgroup><solution><div class=\"detailed-solution\"><p>Explanation</p><p>explanation</p></div></solution></choiceresponse>\n</problem>",
          "has_changes": True,
          "metadata": {
            "display_name": "Multi-select",
            "max_attempts": None,
            "weight": 1,
            "showanswer": None,
            "show_reset_button": None,
            "rerandomize": None,
            "markdown_edited": False
          }
        }
        modify_block_olx(usage_key=problem.usage_key, data=problem_data, user=self.user)
        publish_changes(lib_key_str, self.user)
        logger.info("TEST Created problem content in library block")

        # append_children_to_container(
        #     container_key=unit.container_key,
        #     problem_key=problem.usage_key,
        #     user=self.user
        # )


        # system_role = "Greet the user and say hello world outlining which Llm model is being used!"
        # result = self._call_completion_api(system_role, content_text)

        return {
            "response": f"Hello world from OpenAI model {self.model}!",
            "tokens_used": 0,
            "model_used": self.model,
            "status": "success",
        }

    def anthropic_hello(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Simple test function to call Anthropic API via LiteLLM"""
        system_role = "Greet the user and say hello world outlining which Llm model is being used!"

        result = self._call_completion_api(system_role, content_text)

        return result
