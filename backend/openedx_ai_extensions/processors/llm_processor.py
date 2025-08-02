"""
LLM Processing using LiteLLM for multiple providers
"""
import logging
from litellm import completion
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMProcessor:
    """Handles AI/LLM processing operations"""
    
    def __init__(self, config=None):
        config = config or {}
        
        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})

        logger.warning("")
        logger.warning(f"🤖 WORKFLOW LLMProcessor config: {str(self.config)}")

    def summarize_content(self, content_text, user_query=""):
        """Summarize content using LiteLLM"""
        try:
            # Get config from processor config or settings
            api_key = self.config.get('api_key')
            model = self.config.get('model')
            max_tokens = self.config.get('max_tokens', 500)  # remove this default. If we dont pass it, then use whatever litellm has
            temperature = self.config.get('temperature', 0.7)  # remove this default. If we dont pass it, then use whatever litellm has
            
            if not api_key:
                return {"error": "AI API key not configured"}
            
            system_role = "You are an academic assistant which helps students briefly summarize a unit of content of an online course."

            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": content_text}
                ],
                api_key=api_key,
                max_tokens=max_tokens,
                temperature=temperature
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
