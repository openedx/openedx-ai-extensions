Model Support
#############

Overview
********

The Open edX AI Extensions plugin supports multiple AI model providers across different processor types. While all listed providers are functional and tested, please note that **prompts are optimized for OpenAI models**. When using alternative providers, you may need to adjust prompts for optimal results.

Supported Providers
*******************

The following providers have been tested and verified to work with the plugin:

OpenAI
======

- **Provider**: OpenAI
- **Status**: ✅ Fully Supported & Optimized
- **Model Example**: ``openai/gpt-4o-mini``, ``openai/gpt-5-nano``

Anthropic
=========

- **Provider**: Anthropic (Claude)
- **Status**: ✅ Supported
- **Model Example**: ``anthropic/claude-3-haiku-20240307``
- **Note**: Prompts optimized for OpenAI; may require adjustment

Ollama
======

- **Provider**: Ollama (Local/Self-hosted)
- **Status**: ✅ Supported
- **Model Example**: ``ollama/llama3.2:1b``
- **Note**: Prompts optimized for OpenAI; may require adjustment

Deepseek
========

- **Provider**: Deepseek
- **Status**: ✅ Supported
- **Model Example**: ``huggingface/deepseek-ai/DeepSeek-V3.2:novita``
- **Note**: Prompts optimized for OpenAI; may require adjustment

Processor Compatibility Matrix
*******************************

The following table shows which processors have been tested with each provider:

.. list-table::
   :header-rows: 1
   :widths: 30 17 17 17 17

   * - Processor
     - OpenAI
     - Anthropic
     - Ollama
     - Deepseek
   * - ResponsesProcessor
     - ✅
     - ✅
     - ✅
     - ✅
   * - CompletionProcessor
     - ✅
     - ✅
     - ✅
     - ✅
   * - EducatorAssistantProcessor
     - ✅
     - ✅
     - ✅
     - ✅

Configuration
*************

Plugin Settings
===============

Configure AI providers in your Open edX settings using the ``AI_EXTENSIONS`` configuration:

.. code-block:: python

   AI_EXTENSIONS = {
       "my-openai": {
           "API_KEY": "sk-your-openai-api-key",
           "MODEL": "openai/gpt-4o-mini"
       },
       "my-anthropic": {
           "API_KEY": "sk-ant-your-anthropic-api-key",
           "MODEL": "anthropic/claude-3-haiku-20240307"
       },
       "my-ollama": {
           "API_BASE": "http://your-ollama-server:11434",
           "MODEL": "ollama/llama3.2:1b"
       },
       "my-deepseek": {
           "API_BASE": "https://router.huggingface.co/v1",
           "API_KEY": "hf_your-huggingface-token",
           "MODEL": "huggingface/deepseek-ai/DeepSeek-V3.2:novita"
       }
   }

Configuration Parameters
------------------------

- **API_KEY**: Authentication key for the provider (required for most providers)
- **API_BASE**: Custom API endpoint (optional, required for self-hosted solutions like Ollama)
- **MODEL**: Model identifier in the format ``provider/model-name``

Workflow Configuration
======================

To specify which provider a processor should use, configure it in your workflow JSON configuration file:

.. code-block:: json

   {
     "orchestrator_class": "ThreadedLLMResponse",
     "processor_config": {
       "OpenEdXProcessor": {
         "function": "get_unit_content",
         "char_limit": 300
       },
       "ResponsesProcessor": {
         "function": "chat_with_context",
         "config": "my-openai"
       },
       "SubmissionProcessor": {
         "function": "get_chat_history",
         "max_context_messages": 3
       }
     }
   }

Key Configuration Elements
--------------------------

- **config**: Specifies which AI provider configuration to use (e.g., ``"my-openai"``, ``"my-anthropic"``)
- This must match one of the keys defined in your ``AI_EXTENSIONS`` settings

Switching Providers
===================

To switch between providers, simply change the ``config`` value in your workflow configuration:

.. code-block:: json

   "ResponsesProcessor": {
     "function": "chat_with_context",
     "config": "my-anthropic"  // Changed from "my-openai"
   }

.. warning::
   When switching providers, be aware that:

   - Prompts are optimized for OpenAI's models
   - Different models may interpret instructions differently
   - Response quality and format may vary
   - You may need to adjust system prompts for optimal results with non-OpenAI providers

Best Practices
**************

1. **Start with OpenAI**: For the best out-of-the-box experience, start with OpenAI models as prompts are optimized for them.

2. **Test Thoroughly**: When using alternative providers, thoroughly test your use cases to ensure acceptable response quality.

3. **Adjust Prompts**: Consider customizing system prompts when using non-OpenAI providers for better results.

4. **Monitor Costs**: Be aware that different providers have different pricing structures. Monitor your usage accordingly.

5. **Local Development**: For local development and testing, Ollama provides a cost-effective option with self-hosted models.

6. **API Endpoints**: Ensure your API endpoints are accessible from your Open edX installation, especially for self-hosted solutions like Ollama.

Troubleshooting
***************

Common Issues
=============

**Provider Connection Errors**
   - Verify ``API_BASE`` is correctly configured and accessible
   - Check that API keys are valid and have appropriate permissions
   - Ensure network connectivity to the provider's endpoints

**Unexpected Responses**
   - Remember that prompts are optimized for OpenAI
   - Consider adjusting system prompts for your specific provider
   - Different models have different capabilities and limitations

**Performance Issues**
   - Smaller models (like ``llama3.2:1b``) may have reduced capabilities
   - Consider using more powerful models for complex tasks
   - Self-hosted solutions depend on your hardware capabilities

For additional support, please refer to the project's GitHub repository or contact the development team.
