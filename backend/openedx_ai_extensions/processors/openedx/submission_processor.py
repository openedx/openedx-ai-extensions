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
        self.student_item_dict = {
            "student_id": self.user_session.user.id,
            "course_id": str(self.user_session.course_id),
            "item_id": str(self.user_session.id),
            "item_type": "openedx_ai_extensions_chat",
        }

        # Get max_context_messages from config or settings
        self.max_context_messages = self.config.get(
            "max_context_messages",
            getattr(settings, "AI_EXTENSIONS_MAX_CONTEXT_MESSAGES", 10),
        )

    def process(self, context, input_data=None):
        """Process based on configured function"""
        function_name = self.config.get("function", "get_chat_history")
        function = getattr(self, function_name)
        return function(context, input_data)

    def _process_messages(self, current_messages_count=0, use_max_context=True):
        """
        Retrieve messages from submissions.
        If current_messages_count > 0, return only new messages not already loaded.
        Otherwise, return the most recent messages up to max_context_messages.

        Args:
            current_messages_count: Number of messages already loaded in the frontend

        Returns:
            tuple: (new_messages, has_more) where new_messages is a list of messages
                   and has_more is a boolean indicating if more messages are available
        """
        submissions = submissions_api.get_submissions(self.student_item_dict)
        all_messages = []

        # Extract all messages from all submissions
        # get_submissions returns newest first, so we need to reverse to get chronological order
        for submission in reversed(submissions):
            submission_messages = json.loads(submission["answer"])
            timestamp = str(submission.get("created_at") or submission.get("submitted_at") or "")
            # Remove metadata if present
            if submission_messages and isinstance(submission_messages, list):
                submission_messages_copy = submission_messages.copy()
                if (
                    submission_messages_copy
                    and isinstance(submission_messages_copy[-1], dict)
                    and submission_messages_copy[-1].get("_metadata")
                ):
                    submission_messages_copy.pop()
                # Remove system messages if present
                submission_messages_copy = [
                    msg for msg in submission_messages_copy if msg.get("role") != "system"
                ]
                for msg in submission_messages_copy:
                    if isinstance(msg, dict):
                        msg["timestamp"] = timestamp
                # Extend to maintain chronological order (oldest to newest)
                all_messages.extend(submission_messages_copy)

        if current_messages_count > 0:
            # If current_messages_count provided, return the next batch of older messages
            # Frontend has the most recent current_messages_count messages
            # We need to return the next max_context_messages before those

            if current_messages_count >= len(all_messages):
                # No more messages available
                return [], False

            # Calculate how many messages are left to load
            # Total messages - messages already shown = remaining older messages
            remaining_message_count = len(all_messages) - current_messages_count

            if remaining_message_count <= 0:
                # No more messages available
                return [], False

            # Calculate the slice to get the next batch of older messages
            # We want messages from [end - current_count - max_context : end - current_count]
            if use_max_context:
                start_index = max(
                    0,
                    len(all_messages) - current_messages_count - self.max_context_messages,
                )
                end_index = len(all_messages) - current_messages_count
            else:
                start_index = 0
                end_index = len(all_messages) - current_messages_count

            new_messages = all_messages[start_index:end_index]
            has_more = start_index > 0

            if not new_messages:
                has_more = False
            return new_messages, has_more
        else:
            # Initial load: return most recent messages
            if use_max_context:
                messages = (
                    all_messages[-self.max_context_messages:] if all_messages else []
                )
            else:
                messages = all_messages if all_messages else []
            has_more = len(all_messages) > len(messages)

            return messages, has_more

    def get_chat_history(self, _context, _user_query=None):
        """
        Retrieve initial chat history for the user session.
        Returns the most recent messages up to max_context_messages.
        """
        if self.user_session.local_submission_id:
            messages, has_more = self._process_messages()

            return {
                "response": json.dumps(
                    {
                        "messages": messages,
                        "metadata": {
                            "has_more": has_more,
                            "current_count": len(messages),
                        },
                    }
                ),
            }
        else:
            return {"error": "No submission ID associated with the session"}

    def get_previous_messages(self, current_messages_count=0):
        """
        Retrieve previous messages for lazy loading older chat history.
        Takes the count of current messages from frontend and returns the next batch of older messages.

        Args:
            current_messages_count: Number of messages currently displayed in the frontend

        Returns:
            dict: Contains 'response' (JSON string of new messages) and 'metadata' (has_more flag)
        """
        try:
            # Ensure current_messages_count is an integer
            if isinstance(current_messages_count, str):
                try:
                    current_messages_count = int(current_messages_count)
                except (ValueError, TypeError):
                    current_messages_count = 0

            new_messages, has_more = self._process_messages(
                current_messages_count=current_messages_count
            )

            return {
                "response": json.dumps(
                    {
                        "messages": new_messages,
                        "metadata": {
                            "has_more": has_more,
                            "new_count": len(new_messages),
                        },
                    }
                ),
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error retrieving previous messages: {e}")
            return {"error": f"Failed to load previous messages: {str(e)}"}

    def update_chat_submission(self, messages):
        """
        Update the submission with the LLM response.
        Truncates message history to keep only the most recent messages while
        preserving references to previous submission IDs.
        """

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
                if (
                    existing_messages
                    and isinstance(existing_messages[-1], dict)
                    and existing_messages[-1].get("_metadata")
                ):
                    metadata = existing_messages.pop()
                    previous_submission_ids = (
                        metadata.get("previous_submission_ids", [])
                        + previous_submission_ids
                    )

        # Add metadata to track previous submission IDs
        if previous_submission_ids:
            messages.append(
                {
                    "_metadata": True,
                    "previous_submission_ids": previous_submission_ids,
                }
            )

        self.update_submission(messages)

    def update_submission(self, data):
        """
        Update the submission with provided data.
        """
        submission = submissions_api.create_submission(
            student_item_dict=self.student_item_dict,
            answer=json.dumps(data),
            attempt_number=1,
        )
        self.user_session.local_submission_id = submission["uuid"]
        self.user_session.save()

    def get_submission(self):
        """
        Retrieve the current submission associated with the user session.
        """
        if self.user_session.local_submission_id:
            return submissions_api.get_submission_and_student(
                self.user_session.local_submission_id
            )
        return None

    @staticmethod
    def _normalize_message_content(content):
        """
        Normalize message content to ensure LiteLLM compatibility.

        Args:
            content: The content to normalize (can be str, dict, list, or other)

        Returns:
            Normalized content as string or valid multi-modal list format
        """
        if content is None or isinstance(content, str):
            return content

        if isinstance(content, dict):
            # Convert dict to JSON string for LiteLLM compatibility
            return json.dumps(content)

        if isinstance(content, list):
            # Check if it's valid LiteLLM multi-modal format
            # Valid format: list of dicts with 'type' field (e.g., [{"type": "text", "text": "..."}])
            if content and all(isinstance(item, dict) and "type" in item for item in content):
                return content  # Keep valid multi-modal format
            # Otherwise convert to string
            return str(content)

        # Convert any other type to string
        return str(content)

    def _normalize_message(self, message):
        """
        Normalize a single message for LiteLLM compatibility.

        Args:
            message: The message dict to normalize

        Returns:
            Normalized message dict with proper content format and cleaned fields
        """
        if not isinstance(message, dict):
            return message

        normalized = message.copy()
        normalized["content"] = self._normalize_message_content(normalized.get("content"))
        # Remove timestamp field as it's not part of standard message schema
        normalized.pop("timestamp", None)
        return normalized

    def get_full_message_history(self):
        """
        Retrieve the full message history for the current submission.
        Ensures all message content is properly formatted for LiteLLM compatibility.

        Returns:
            List of normalized messages or None if no submission exists
        """
        if not self.user_session.local_submission_id:
            return None

        messages, _ = self._process_messages(use_max_context=False)
        return [self._normalize_message(msg) for msg in messages]
