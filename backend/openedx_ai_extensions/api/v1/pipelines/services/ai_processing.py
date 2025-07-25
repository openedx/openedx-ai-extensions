"""
AI Processing Services
Functions for AI operations using LiteLLM for multiple providers
"""
import logging
from litellm import completion
from django.conf import settings

logger = logging.getLogger(__name__)

def summarize_content(content_text, user_query=""):
    """
    Summarize unit content using LiteLLM (supports OpenAI, Anthropic, etc.)
    """
    try:
        # Get API configuration from settings
        api_key = settings.OPENAI_API_KEY
        model = settings.AI_MODEL
        
        if not api_key:
            return {"error": "AI API key not configured"}
        
        system_role = "You are an academic assistant which helps students briefly summarize a unit of content of an online course."

        # Call LiteLLM (automatically handles different providers)
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": content_text}
            ],
            api_key=api_key,
            max_tokens=500,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content
        
        return {
            "summary": summary,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "model_used": model,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error calling LiteLLM: {e}")
        return {"error": f"AI processing failed: {str(e)}"}