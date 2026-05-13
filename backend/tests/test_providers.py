"""
Tests for processors/llm/providers — provider capability registry,
adapt_to_provider, and _apply_multi_turn_cache.

Focus: Anthropic multi-turn flow where the full message history is sent on
every request and cache_control breakpoints are applied to the last system
and last user messages.
"""
# pylint: disable=invalid-sequence-index

from openedx_ai_extensions.processors.llm.providers import _apply_multi_turn_cache, adapt_to_provider, provider_supports


def _make_session(remote_response_id=None, local_submission_id=None):
    """Return a minimal mock session object."""
    session = type("Session", (), {
        "remote_response_id": remote_response_id,
        "local_submission_id": local_submission_id,
        "save": lambda self: None,
    })()
    return session


def _roles(messages):
    """Return the list of roles from a message list."""
    return [m.get("role") for m in messages]


def _cache_controlled_indices(messages):
    """Return indices of messages that carry cache_control."""
    result = []
    for i, msg in enumerate(messages):
        content = msg.get("content")
        if isinstance(content, list) and any("cache_control" in b for b in content):
            result.append(i)
    return result


class TestProviderSupports:
    """Tests for provider_supports function."""

    def test_openai_server_side_thread_id(self):
        assert provider_supports("openai", "server_side_thread_id") is True

    def test_anthropic_multi_turn_cache(self):
        assert provider_supports("anthropic", "multi_turn_cache") is True

    def test_anthropic_does_not_support_server_side_thread_id(self):
        assert provider_supports("anthropic", "server_side_thread_id") is False

    def test_openai_does_not_support_multi_turn_cache(self):
        assert provider_supports("openai", "multi_turn_cache") is False

    def test_unknown_provider_returns_false(self):
        assert provider_supports("unknown_llm", "multi_turn_cache") is False

    def test_unknown_capability_returns_false(self):
        assert provider_supports("anthropic", "nonexistent_capability") is False


class TestApplyMultiTurnCache:
    """Tests for _apply_multi_turn_cache function."""

    def _system(self, text):
        return {"role": "system", "content": text}

    def _user(self, text):
        return {"role": "user", "content": text}

    def _assistant(self, text):
        return {"role": "assistant", "content": text}

    def test_marks_last_system_and_last_user(self):
        messages = [
            self._system("You are a helpful assistant."),
            self._system("Course context: unit 1 content."),
            self._user("What is this about?"),
            self._assistant("It is about unit 1."),
            self._user("Tell me more."),
        ]
        result = _apply_multi_turn_cache(messages)

        # Only 2 breakpoints: last system (idx 1) and last user (idx 4)
        assert _cache_controlled_indices(result) == [1, 4]

    def test_non_targeted_messages_are_unchanged(self):
        messages = [
            self._system("System A."),
            self._system("System B."),
            self._user("Question 1?"),
            self._assistant("Answer 1."),
            self._user("Question 2?"),
        ]
        result = _apply_multi_turn_cache(messages)

        # First system, first user, and assistant are plain strings
        assert isinstance(result[0]["content"], str)
        assert isinstance(result[2]["content"], str)
        assert isinstance(result[3]["content"], str)

    def test_content_wrapped_in_text_block(self):
        messages = [
            self._system("Stable system prompt."),
            self._user("Current question."),
        ]
        result = _apply_multi_turn_cache(messages)

        system_content = result[0]["content"]
        user_content = result[1]["content"]

        assert isinstance(system_content, list)
        assert system_content[0]["type"] == "text"
        assert system_content[0]["text"] == "Stable system prompt."
        assert system_content[0]["cache_control"] == {"type": "ephemeral"}

        assert isinstance(user_content, list)
        assert user_content[0]["text"] == "Current question."
        assert user_content[0]["cache_control"] == {"type": "ephemeral"}

    def test_original_message_dict_is_not_mutated(self):
        original = {"role": "system", "content": "Unchanged."}
        messages = [original, {"role": "user", "content": "Q?"}]
        _apply_multi_turn_cache(messages)
        assert original["content"] == "Unchanged."

    def test_no_user_message_only_marks_system(self):
        messages = [
            self._system("System only."),
        ]
        result = _apply_multi_turn_cache(messages)
        assert _cache_controlled_indices(result) == [0]

    def test_no_system_message_only_marks_user(self):
        messages = [
            self._user("No system here."),
            self._assistant("Reply."),
            self._user("Follow-up."),
        ]
        result = _apply_multi_turn_cache(messages)
        assert _cache_controlled_indices(result) == [2]

    def test_long_conversation_still_uses_two_breakpoints(self):
        """The 2-breakpoint strategy must hold regardless of conversation length."""
        messages = [self._system("Ctx.")]
        for i in range(10):
            messages.append(self._user(f"Q{i}"))
            messages.append(self._assistant(f"A{i}"))
        messages.append(self._user("Final question."))

        result = _apply_multi_turn_cache(messages)
        assert len(_cache_controlled_indices(result)) == 2

    def test_already_block_format_content_is_not_double_wrapped(self):
        """If content is already a list (not a string), it is left as-is."""
        block_content = [{"type": "text", "text": "Already wrapped."}]
        messages = [
            {"role": "system", "content": block_content},
            {"role": "user", "content": "Question."},
        ]
        result = _apply_multi_turn_cache(messages)
        # System was already a list — not re-wrapped
        assert result[0]["content"] is block_content
        # User (string) is wrapped normally
        assert isinstance(result[1]["content"], list)


class TestAdaptToProviderAnthropic:
    """
    Verify that adapt_to_provider correctly handles the Anthropic case:
    - Full message history is sent on every request (no server-side threading)
    - cache_control breakpoints are applied to last system + last user messages
    - The input→messages conversion for streaming works alongside caching
    """

    def _base_params(self, stream=False):
        return {
            "stream": stream,
            "input": [
                {"role": "system", "content": "You are a course assistant."},
                {"role": "system", "content": "Course context: chapter 3."},
                {"role": "user", "content": "Summarize chapter 3."},
                {"role": "assistant", "content": "Chapter 3 covers..."},
                {"role": "user", "content": "What are the key points?"},
            ],
        }

    def test_cache_applied_to_last_system_and_last_user(self):
        params = self._base_params()
        result = adapt_to_provider("anthropic", params)

        msgs = result["input"]
        cached = _cache_controlled_indices(msgs)
        # Last system is index 1, last user is index 4
        assert cached == [1, 4]

    def test_all_five_messages_are_present(self):
        """No messages are dropped — full history is sent."""
        params = self._base_params()
        result = adapt_to_provider("anthropic", params)
        assert len(result["input"]) == 5

    def test_roles_preserved(self):
        params = self._base_params()
        result = adapt_to_provider("anthropic", params)
        assert _roles(result["input"]) == [
            "system", "system", "user", "assistant", "user"
        ]

    def test_assistant_message_not_cached(self):
        params = self._base_params()
        result = adapt_to_provider("anthropic", params)
        assistant_msg = result["input"][3]
        assert isinstance(assistant_msg["content"], str)

    def test_streaming_converts_input_to_messages_then_caches(self):
        """For streaming, input is renamed to messages before caching runs."""
        params = self._base_params(stream=True)
        result = adapt_to_provider("anthropic", params)

        assert "input" not in result
        assert "messages" in result
        msgs = result["messages"]
        assert len(msgs) == 5
        assert _cache_controlled_indices(msgs) == [1, 4]

    def test_no_server_side_thread_id_set(self):
        """Anthropic must never receive previous_response_id."""
        session = _make_session(remote_response_id="some-id")
        params = self._base_params()
        result = adapt_to_provider(
            "anthropic", params, user_session=session, input_data="What are the key points?"
        )
        assert "previous_response_id" not in result

    def test_dummy_user_message_injected_when_no_user_message(self):
        """Anthropic requires at least one user message; a dummy is added if missing."""
        params = {
            "stream": False,
            "input": [
                {"role": "system", "content": "You are a course assistant."},
                {"role": "system", "content": "Course context."},
            ],
        }
        result = adapt_to_provider("anthropic", params, has_user_input=False)
        roles = _roles(result["input"])
        assert "user" in roles

    def test_dummy_message_also_gets_cache_control(self):
        """The injected dummy user message is the last user message, so it gets cached."""
        params = {
            "stream": False,
            "input": [
                {"role": "system", "content": "System prompt."},
            ],
        }
        result = adapt_to_provider("anthropic", params, has_user_input=False)
        # The dummy user message should be the last and should carry cache_control
        last = result["input"][-1]
        assert last["role"] == "user"
        assert isinstance(last["content"], list)
        assert last["content"][0]["cache_control"] == {"type": "ephemeral"}


class TestAdaptToProviderOpenAIUnaffected:
    """Tests for adapt_to_provider with OpenAI."""

    def test_openai_input_not_cache_transformed(self):
        params = {
            "stream": False,
            "input": [
                {"role": "system", "content": "Sys."},
                {"role": "user", "content": "Q?"},
            ],
        }
        result = adapt_to_provider("openai", params)
        for msg in result["input"]:
            assert isinstance(msg["content"], str)
