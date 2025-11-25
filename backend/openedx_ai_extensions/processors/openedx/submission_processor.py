"""
Submission processor for handling OpenEdX submissions
"""

import json
import logging

from django.conf import settings
from submissions import api as submissions_api

logger = logging.getLogger(__name__)


class SubmissionProcessor:
    """Handles OpenEdX submission operations for chat history and persistence"""

    def __init__(self, config=None, user_session=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})
        self.user_session = user_session

        # Get max_context_messages from config or settings
        self.max_context_messages = self.config.get(
            "max_context_messages",
            getattr(settings, "AI_EXTENSIONS_MAX_CONTEXT_MESSAGES", 3)
        )

    def process(self, context, input_data=None):
        """Process based on configured function"""
        function_name = self.config.get("function", "get_chat_history")
        function = getattr(self, function_name)
        return function(context, input_data)

    def _proccess_messages(self, local_submission_id):
        """
        Retrieve messages and previous submission IDs from a submission.
        """
        submission = submissions_api.get_submission_and_student(local_submission_id)
        messages = submission["answer"]
        if messages and isinstance(messages, list):
            # Remove metadata entry if present (it's always the last item)
            if messages and isinstance(messages[-1], dict) and messages[-1].get("_metadata"):
                metadata = messages.pop()
                previous_submission_ids = metadata.get("previous_submission_ids", [])
                # while messagges list < self.max_context_messages, get more from previous submissions
                while len(messages) < self.max_context_messages and previous_submission_ids:
                    prev_id = previous_submission_ids.pop()
                    prev_submission = submissions_api.get_submission_and_student(prev_id)
                    prev_messages = prev_submission["answer"]
                    # Remove metadata if present
                    if prev_messages and isinstance(prev_messages, list):
                        if prev_messages and isinstance(prev_messages[-1], dict) and prev_messages[-1].get("_metadata"):
                            prev_messages.pop()
                    # Prepend previous messages
                    messages = prev_messages + messages
                return messages, previous_submission_ids
        return messages, []

    def get_chat_history(self, _context, _user_query=None):
        """
        Retrieve chat history for the user session.
        Filters out metadata entries before returning messages.
        Returns metadata separately to inform frontend about available history.
        """

        if self.user_session.local_submission_id:
            messages, previous_submission_ids = self._proccess_messages(self.user_session.local_submission_id)

            return {
                "response": json.dumps({
                    "messages": messages,
                    "metadata": {
                        "previous_submission_ids": previous_submission_ids,
                        "has_more": len(previous_submission_ids) > 0,
                    },
                }),
            }
        else:
            return {"error": "No submission ID associated with the session"}

    def get_previous_messages(self, submission_id):
        """
        Retrieve messages from a specific previous submission ID.
        Used for lazy loading older chat history when scrolling up.

        Args:
            submission_id: The UUID of the submission to retrieve

        Returns:
            dict: Contains 'response' (JSON string of messages) and 'metadata' (previous submission IDs)
        """
        try:
            messages, previous_submission_ids = self._proccess_messages(submission_id)

            return {
                "response": json.dumps(messages),
                "metadata": {
                    "previous_submission_ids": previous_submission_ids,
                    "has_more": len(previous_submission_ids) > 0,
                },
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error retrieving previous messages for submission {submission_id}: {e}")
            return {"error": f"Failed to load previous messages: {str(e)}"}

    def update_submission(self, llm_response, user_query):
        """
        Update the submission with the LLM response.
        Truncates message history to keep only the most recent messages while
        preserving references to previous submission IDs.
        """

        student_item_dict = {
            "student_id": self.user_session.user.id,
            "course_id": self.user_session.course_id,
            "item_id": self.user_session.location_id,
            "item_type": "openedx_ai_extensions_chat",
        }

        messages = [
            {"role": "assistant", "content": llm_response},
        ]

        if user_query:
            messages.insert(0, {"role": "user", "content": user_query})

        # Track previous submission IDs for reference
        previous_submission_ids = []

        if self.user_session.local_submission_id:
            submission = submissions_api.get_submission_and_student(
                self.user_session.local_submission_id
            )

            # Store current submission ID as previous
            previous_submission_ids.append(self.user_session.local_submission_id)

            # Get existing messages and any previously tracked submission IDs
            existing_messages = submission["answer"]

            # Extract metadata if it exists (for tracking previous submission IDs)
            if existing_messages and isinstance(existing_messages, list):
                # Check if the last item is metadata
                if existing_messages and isinstance(existing_messages[-1], dict) and \
                   existing_messages[-1].get("_metadata"):
                    metadata = existing_messages.pop()
                    previous_submission_ids = metadata.get("previous_submission_ids", []) + previous_submission_ids

        # Add metadata to track previous submission IDs
        if previous_submission_ids:
            messages.append({
                "_metadata": True,
                "previous_submission_ids": previous_submission_ids,
            })

        submission = submissions_api.create_submission(
            student_item_dict=student_item_dict,
            answer=messages,
            attempt_number=1,
        )
        self.user_session.local_submission_id = submission["uuid"]
        self.user_session.save()
