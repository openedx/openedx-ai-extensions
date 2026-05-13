"""
Provider-specific quirks and adaptations for different LLM providers.
"""

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
}


def provider_supports(provider, capability):
    """Return True if the given provider supports the named capability."""
    return capability in _PROVIDER_CAPABILITIES.get(provider, set())


# TODO: refactor this module to make it more extensible for future providers
def adapt_to_provider(
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
        # Anthropic requires at least one user message in the conversation
        if not has_user_input:
            # Check if there's already a user message
            has_user_msg = any(
                msg.get("role") == "user"
                for msg in params.get("input", params.get("messages", []))
            )

            if not has_user_msg:
                # Add a generic user message to satisfy Anthropic's requirements
                user_prompt = "Please provide the requested information based on the context above."

                if "input" in params:
                    params["input"].append({"role": "user", "content": user_prompt})
                elif "messages" in params:
                    params["messages"].append({"role": "user", "content": user_prompt})

    if not provider_supports(provider, "server_side_thread_id") and params.get("stream") and "input" in params:
        # Non-OpenAI providers: convert Responses API shape → Completion API
        # shape so that completion() / _completion_with_tools() can be called
        # directly, ensuring tool-call events are visible during streaming.
        params["messages"] = params.pop("input")
        for key in ("previous_response_id", "store", "truncation"):
            params.pop(key, None)

    return params


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
