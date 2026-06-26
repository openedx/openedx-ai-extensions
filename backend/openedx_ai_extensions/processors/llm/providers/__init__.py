"""
Provider-specific quirks and adaptations for different LLM providers.
"""
import logging

logger = logging.getLogger(__name__)

_PROVIDER_CAPABILITIES = {
    "openai": {
        # Provider stores conversation history server-side and returns a response ID.
        # Subsequent turns send only the new user message + that ID; the provider
        # reconstructs context itself. Without this, full history is fetched from local
        # storage and sent on every request.
        # Affects: adapt_to_provider (sets previous_response_id, replaces input with new
        # user message only), after_tool_call_adaptations (persists new response ID),
        # _call_responses_wrapper (skips saving remote_response_id for providers without it).
        "server_side_thread_id",
    },
    "anthropic": {
        # Provider supports prompt caching via cache_control on content blocks. Cached
        # prefixes are reused at ~10% of normal input token cost for a 5-minute window.
        # Without this, every request pays full price for system context and history.
        # Two breakpoints per request: last system message (stable course context) and last
        # user message (becomes the lookback target for the next turn). See ADR 0010.
        # Affects: adapt_to_provider (_apply_multi_turn_cache).
        "multi_turn_cache",
    },
}


def provider_supports(provider, capability):
    """Return True if the given provider supports the named capability."""
    return capability in _PROVIDER_CAPABILITIES.get(provider, set())


# TODO: refactor this module to make it more extensible for future providers
def adapt_to_provider(  # pylint: disable=unused-argument
        provider, params, *, has_user_input=True, user_session=None,
        input_data=None):
    """
    Apply provider-specific modifications to API call parameters.

    This function centralizes all provider-specific logic that was previously
    scattered throughout the codebase (e.g., OpenAI-specific threading,
    Anthropic's requirement for user messages).

    For non-OpenAI providers that are streaming with Responses API params
    (i.e. ``input`` key present), the parameters are automatically converted
    to Completion API format (``messages``) because LiteLLM's Responses API
    streaming translation does not surface tool-call events correctly for
    those providers.  Callers can check for the ``"messages"`` key in the
    returned dict to decide whether to use the Completion API path.

    Args:
        provider (str): The LLM provider name (e.g., 'openai', 'anthropic')
        params (dict): The parameters dictionary to modify
        has_user_input (bool): Whether the conversation includes user input
        user_session: Optional user session for threading support
        input_data: Optional input data for continuing conversations

    Returns:
        dict: Modified parameters with provider-specific adaptations applied
    """
    if provider_supports(provider, "server_side_thread_id"):
        if user_session and user_session.remote_response_id and input_data:
            params["previous_response_id"] = user_session.remote_response_id
            if "input" in params:
                params["input"] = [{"role": "user", "content": input_data}]

    if provider == "anthropic":
        # Anthropic requires at least one user message in the conversation.
        # Check unconditionally: input_data may be present but never added to the
        # input list (e.g. initial chat_with_context call where _build_response_api_params
        # only puts system messages in params["input"]).
        msgs = params.get("input", params.get("messages", []))
        has_user_msg = any(msg.get("role") == "user" for msg in msgs)
        if not has_user_msg:
            key = "input" if "input" in params else "messages"
            if input_data:
                user_content = input_data if isinstance(input_data, str) else str(input_data)
                params[key].append({"role": "user", "content": user_content})
            else:
                params[key].append({
                    "role": "user",
                    "content": "Please provide the requested information based on the context above.",
                })

    if not provider_supports(provider, "server_side_thread_id") and params.get("stream") and "input" in params:
        # Non-OpenAI providers: convert Responses API shape → Completion API
        # shape so that completion() / _completion_with_tools() can be called
        # directly, ensuring tool-call events are visible during streaming.
        params["messages"] = params.pop("input")
        for key in ("previous_response_id", "store", "truncation"):
            params.pop(key, None)

    if provider_supports(provider, "multi_turn_cache"):
        key = "messages" if "messages" in params else "input"
        if key in params:
            params[key] = _apply_multi_turn_cache(params[key])

    return params


def _apply_multi_turn_cache(messages):
    """
    Add Anthropic style cache_control breakpoints to the last system and last user messages.

    Two breakpoints are sufficient for any conversation length:
    - Last system message: stable across all turns (course context never changes).
    - Last user message: becomes the lookback target for the next turn. The 20-block
      lookback window finds the previous turn's cache entry within 2 steps (one
      assistant + one user block), so no additional breakpoints are needed regardless
      of conversation length.

    History is always stored as plain strings (get_full_message_history filters out
    non-string content), so this transformation is request-only and never persisted.
    """
    last_system_idx = None
    last_user_idx = None
    for i, msg in enumerate(messages):
        role = msg.get("role")
        if role == "system":
            last_system_idx = i
        elif role == "user":
            last_user_idx = i

    result = list(messages)
    for idx in (last_system_idx, last_user_idx):
        if idx is None:
            continue
        msg = result[idx]
        content = msg.get("content", "")
        if isinstance(content, str):
            result[idx] = {
                **msg,
                "content": [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}],
            }
        else:
            logger.warning(
                "multi_turn_cache: skipping cache_control on role=%r message at index %d "
                "— content is %s, not a plain string. Cache breakpoint will be missing for this turn.",
                msg.get("role"), idx, type(content).__name__,
            )
    return result


def after_tool_call_adaptations(provider, params, data=None):
    """
    Apply provider-specific modifications to API call parameters after tool calls.

    This function centralizes all provider-specific logic that needs to be applied
    after tool calls have been made, such as updating threading information.

    Args:
        provider (str): The LLM provider name (e.g., 'openai', 'anthropic')
        params (dict): The parameters dictionary to modify
    Returns:
        dict: Modified parameters with provider-specific adaptations applied
    """
    if provider_supports(provider, "server_side_thread_id"):
        if data and hasattr(data, "id"):
            params["previous_response_id"] = data.id

    return params
