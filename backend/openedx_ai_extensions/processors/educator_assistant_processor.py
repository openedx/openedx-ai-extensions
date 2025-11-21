"""
LLM Processing using LiteLLM for multiple providers
"""

import json
import logging

from django.conf import settings
from litellm import completion
from .content_libraries_utils import create_block, modify_block_olx
from uuid import uuid4

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

    def _call_completion_api(self, system_role, user_content=None):
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

    def generate_quiz_questions(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Generate quiz questions based on the content provided"""

        lib_name = "demo1:demo1"
        lib_key_str = f"lib:{lib_name}"

        requested_questions = 2

        prompt = f"""
          You must generate a set of assessment questions in valid OLX format based on the following context about an unit of online course:

          CONTEXT: --------
            {self.context}
          --------

          Generate exactly [{requested_questions}] questions.

          The following rules are MANDATORY:

          1. The output must be a VALID JSON array. No text outside the JSON.
          2. Each item in the array must be an object with EXACTLY these fields:
            - "category": always "problem"
            - "display_name": a short identifier for the problem type (e.g., "multi-choice", "single_select", "dropdown", "numeric", "text")
            - "data": the OLX markup for the problem
          3. All OLX markup must strictly follow the Open edX OLX specification:
            https://docs.openedx.org/en/latest/educators/olx/front_matter/read_me.html
          4. Each question must be complete, including:
            - A <div> containing the question prompt
            - A valid OLX response type such as:
              - <multiplechoiceresponse> with <choicegroup> and <choice>
              - <choiceresponse> with <checkboxgroup>
              - <optionresponse> with <optioninput>
              - or any other valid OLX problem format
            - A <solution> element with explanation paragraphs
          5. Do NOT use any different formats, only the given example formats.
          5. Ensure the JSON contains no markdown, no escaping, and no additional comments.

          Example formats you may follow:

          Multiple choice example:
          {{
            "category": "problem",
            "display_name": "multi-choice",
            "data": "<problem><multiplechoiceresponse><div>question</div><choicegroup><choice correct=\\"true\\"><div>a</div></choice><choice correct=\\"false\\"><div>b</div></choice><choice correct=\\"false\\"><div>c</div></choice></choicegroup><solution><div class=\\"detailed-solution\\"><p>Explanation</p><p>explanation</p></div></solution></multiplechoiceresponse></problem>"
          }}

          Checkbox example:
          {{
            "category": "problem",
            "display_name": "single_select",
            "data": "<problem><choiceresponse><div>question</div><checkboxgroup><choice correct=\\"true\\"><div>1</div></choice><choice correct=\\"false\\"><div>2</div></choice><choice correct=\\"false\\"><div>3</div></choice></checkboxgroup><solution><div class=\\"detailed-solution\\"><p>Explanation</p><p>explanation</p></div></solution></choiceresponse></problem>"
          }}

          Dropdown example:
          {{
            "category": "problem",
            "display_name": "dropdown",
            "data": "<problem><optionresponse><div>question</div><optioninput><option correct=\\"true\\">a</option><option correct=\\"false\\">b</option><option correct=\\"false\\">c</option></optioninput><solution><div class=\\"detailed-solution\\"><p>Explanation</p><p>explanation</p></div></solution></optionresponse></problem>"
          }}

          Now generate the JSON array of [{requested_questions}] OLX questions.
        """

        result = self._call_completion_api(prompt)

        json_response = json.loads(result['response'])

        for problem_info in json_response:

            block_data = {
              "block_type": problem_info['category'],
              "definition_id": str(uuid4()),
              "can_stand_alone": True,
            }

            problem = create_block(lib_key_str, self.user, block_data)

            problem_data = {
              "category": problem_info['category'],
              "courseKey": lib_key_str,
              "data": problem_info['data'],
              "has_changes": True,
              "metadata": {
                "display_name": problem_info['display_name'],
                "max_attempts": None,
                "weight": 1,
                "showanswer": None,
                "show_reset_button": None,
                "rerandomize": None,
                "markdown_edited": False
              }
            }
            modify_block_olx(usage_key=problem.usage_key, data=problem_data, user=self.user)

        return {
            "response": f"Hello world from OpenAI model {self.model}!",
            "tokens_used": 0,
            "model_used": self.model,
            "status": "success",
        }
