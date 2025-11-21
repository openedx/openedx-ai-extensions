"""
LLM Processing using LiteLLM for multiple providers
"""

import json
import logging

from submissions import api as submissions_api

logger = logging.getLogger(__name__)


class SubmissionProcessor:
    """Handles AI/LLM processing operations"""

    def __init__(self, config=None, user_session=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})
        self.user_session = user_session

    def process(self, context, input_data=None):
        """Process based on configured function"""
        function_name = self.config.get("function", "get_chat_history")
        function = getattr(self, function_name)
        return function(context, input_data)

    def get_chat_history(self, _context, _user_query=None):
        """
        Retrieve chat history for the user session.
        """

        if self.user_session.local_submission_id:
            submission = submissions_api.get_submission_and_student(
                self.user_session.local_submission_id
            )
            return {
                "response": json.dumps(submission["answer"]),
            }
        else:
            return {"error": "No submission ID associated with the session"}

    def update_submission(self, llm_response, user_query):
        """
        Update the submission with the LLM response.
        """

        student_item_dict = {
            "student_id": self.user_session.user.id,
            "course_id": self.user_session.course_id,
            "item_id": self.user_session.unit_id,
            "item_type": "openedx_ai_extensions_chat",
        }

        messages = [
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": llm_response},
        ]

        if self.user_session.local_submission_id:
            submission = submissions_api.get_submission_and_student(
                self.user_session.local_submission_id
            )
            messages = submission["answer"] + messages
        submission = submissions_api.create_submission(
            student_item_dict=student_item_dict,
            answer=messages,
            attempt_number=1,
        )
        self.user_session.local_submission_id = submission["uuid"]
        self.user_session.save()
