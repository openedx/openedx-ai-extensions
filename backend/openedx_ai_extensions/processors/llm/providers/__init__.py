"""
Provider-specific quirks and adaptations for different LLM providers.
"""


# TODO: refactor this module to make it more extensible for future providers
def adapt_to_provider(provider, params, has_user_input=True, user_session=None, input_data=None):
    """
    Apply provider-specific modifications to API call parameters.

    This function centralizes all provider-specific logic that was previously
    scattered throughout the codebase (e.g., OpenAI-specific threading,
    Anthropic's requirement for user messages).

    Args:
        provider (str): The LLM provider name (e.g., 'openai', 'anthropic')
        params (dict): The parameters dictionary to modify
        has_user_input (bool): Whether the conversation includes user input
        user_session: Optional user session for threading support
        input_data: Optional input data for continuing conversations

    Returns:
        dict: Modified parameters with provider-specific adaptations applied
    """
    if provider == "openai":
        # OpenAI supports threading via previous_response_id
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
    if provider == "openai":
        if data and hasattr(data, "id"):
            params["previous_response_id"] = data.id

    return params
