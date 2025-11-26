"""
LLM Processing using LiteLLM for multiple providers
"""

import json
import logging

from django.conf import settings
from litellm import completion

from .content_libraries_utils import ContentLibraryHelper

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
        lib_key_str = input_data.get('library_id')
        requested_questions = input_data.get('num_questions')
        extra_instructions = input_data.get('extra_instructions')

        prompt = f"""
          You must generate a set of assessment questions in valid OLX format based on
          the following context about an unit of online course:

          CONTEXT: --------
            {self.context}
          --------

          Generate exactly [{requested_questions}] questions.

          The following rules are MANDATORY:

          1. The output must be a VALID JSON. No text outside the JSON. following output structure:
            {{
              'collection': 'Name of the collection based on the course context',
              'items': [
                {{
                  "category": "problem",
                  "data": "<OLX markup here>"
                }},
                ...
              ]
            }}
          2. Each item in the array must be an object with EXACTLY these fields:
            - "category": always "problem"
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
          5. Do NOT use any different formats, only the given example formats. You can look for reference at:
                https://github.com/openedx/training-courses/tree/main/olx_example_course/course/problem
          5. Ensure the JSON contains no markdown, no escaping, and no additional comments.

          Example formats you may follow:

          Dropdown example:
          {{
            "category": "problem",
            "data": "<problem display_name=\"Dropdown\" markdown_edited=\"false\" rerandomize=\"never\" \
show_reset_button=\"false\" showanswer=\"finished\" weight=\"1.0\">
              <optionresponse>
                <div>What is the correct answer?</div>
                <optioninput>
                  <option correct="false">Incorrect</option>
                  <option correct="true">Correct</option>
                  <option correct="false">Incorrect</option>
                </optioninput>
                <solution>
                  <div class="detailed-solution">
                    <p>Explanation</p>
                    <p>The correct answer is called "correct"</p>
                  </div>
                </solution>
              </optionresponse>
            </problem>"
          }}

          Multi Select example:
          {{
            "category": "problem",
            "data": "<problem display_name=\"Multi-select\" markdown_edited=\"false\" max_attempts=\"2\" \
rerandomize=\"never\" show_reset_button=\"false\" showanswer=\"finished\" weight=\"5.0\">
              <choiceresponse>
                <div>What are the correct answers?</div>
                <checkboxgroup>
                  <choice correct="true">
                    <div>Correct</div>
                  </choice>
                  <choice correct="false">
                    <div>Incorrect</div>
                  </choice>
                  <choice correct="true">
                    <div>Correct</div>
                  </choice>
                </checkboxgroup>
                <solution>
                  <div class="detailed-solution">
                    <p>Explanation</p>
                    <p>The correct answers are marked with "correct"</p>
                  </div>
                </solution>
              </choiceresponse>
            </problem>"
          }}

          Single Select example:
          {{
            "category": "problem",
            "data": "<problem display_name=\"Single select\" markdown_edited=\"false\" rerandomize=\"never\" \
show_reset_button=\"false\" showanswer=\"finished\" submission_wait_seconds=\"0\" weight=\"2.0\">
              <multiplechoiceresponse>
                <div>What is the correct answer?</div>
                <choicegroup>
                  <choice correct="false">
                    <div>Incorrect</div>
                  </choice>
                  <choice correct="false">
                    <div>Incorrect</div>
                  </choice>
                  <choice correct="true">
                    <div>Correct</div>
                  </choice>
                </choicegroup>
                <solution>
                  <div class="detailed-solution">
                    <p>Explanation</p>
                    <p>The correct answer is called "Correct"</p>
                  </div>
                </solution>
              </multiplechoiceresponse>
            </problem>"
          }}

          Now generate the JSON of [{requested_questions}] OLX questions.

          Finally some notes passed by the working course author: --------
            {extra_instructions}
          --------
        """

        result = self._call_completion_api(prompt)
        tokens_used = result.get("tokens_used", 0)

        library_helper = ContentLibraryHelper(library_key=lib_key_str, user=self.user)

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

        collection_key = library_helper.create_collection_and_add_items(
            title=response.get("collection", "AI Generated Questions"),
            description="AI-generated quiz questions",
            items=response["items"]
        )

        return {
            "response": f"authoring/library/{lib_key_str}/collection/{collection_key}",
            "tokens_used": tokens_used,
            "model_used": self.model,
            "status": "success",
        }
