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

    def _process_messages(
        self,
        current_messages_count=0,
        use_max_context=True,
        include_submission_id=False,
    ):
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
            if submission_messages and isinstance(submission_messages, list):
                # Remove system messages if present
                submission_messages_copy = [
                    msg for msg in submission_messages if isinstance(msg, dict) and msg.get("role") != "system"
                ]
                submission_uuid = submission.get("uuid", "")
                for msg in submission_messages_copy:
                    msg["timestamp"] = timestamp
                    if include_submission_id:
                        msg["submission_id"] = submission_uuid
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

    def update_chat_submission(self, messages):
        """
        Create a new immutable Submission record for this interaction.

        Each call stores the provided messages (prompt + AI response) as a new
        Submission.  History is tracked implicitly via ``attempt_number``, which
        the Submissions API auto-increments for the same ``student_item``.
        """
        self.update_submission(messages)

    def update_submission(self, data):
        """
        Create a new Submission record with the provided data.

        ``attempt_number`` is intentionally omitted so the Submissions API
        auto-increments it for the given ``student_item``.
        """
        submission = submissions_api.create_submission(
            student_item_dict=self.student_item_dict,
            answer=json.dumps(data),
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

    def get_full_message_history(self):
        """
        Retrieve the full message history for the current submission.
        """
        if self.user_session.local_submission_id:
            messages, _ = self._process_messages(use_max_context=False)
            cleaned = []
            for msg in messages:
                if isinstance(msg, dict):
                    msg.pop("timestamp", None)
                    # Only validate content for role-based messages (user/assistant/system).
                    # Function call/output items use other fields (type, call_id, etc.) and
                    # legitimately have no content field — never filter those out.
                    if "role" in msg:
                        content = msg.get("content")
                        if not isinstance(content, str) or not content:
                            continue
                cleaned.append(msg)
            return cleaned
        else:
            return None

    def get_full_thread(self):
        """
        Retrieve the full message history with timestamps for debugging.

        Uses the submission's own student_item to ensure the lookup key matches
        what was used at creation time, even if the session's fields have changed.

        Returns:
            list: All messages in chronological order with role, content, and timestamp,
                  or None if no submission exists.
        """
        if not self.user_session.local_submission_id:
            return None

        # Look up the submission directly by UUID to get the original student_item
        submission = submissions_api.get_submission_and_student(
            self.user_session.local_submission_id
        )
        original_student_item = submission.get("student_item", {})

        # Use the original student_item for the lookup so it matches
        saved_dict = self.student_item_dict
        self.student_item_dict = {
            "student_id": original_student_item.get(
                "student_id", saved_dict["student_id"]
            ),
            "course_id": original_student_item.get(
                "course_id", saved_dict["course_id"]
            ),
            "item_id": original_student_item.get("item_id", saved_dict["item_id"]),
            "item_type": original_student_item.get(
                "item_type", saved_dict["item_type"]
            ),
        }
        try:
            messages, _ = self._process_messages(
                use_max_context=False, include_submission_id=True
            )
            # Sort by timestamp to guarantee chronological order
            messages.sort(key=lambda m: m.get("timestamp", ""))
            return messages
        finally:
            self.student_item_dict = saved_dict
