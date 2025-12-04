WorkflowConfig Examples
#######################

This document provides examples of ``AIWorkflowConfig`` configurations that demonstrate different AI workflow patterns. These JSON configuration files define how AI workflows behave, including their orchestrator, processors, and UI components.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
********

The ``AIWorkflowConfig`` model stores configuration templates for AI workflows. Each configuration includes:

- **orchestrator_class**: The workflow orchestration pattern
- **processor_config**: Settings for data processing and LLM interactions
- **actuator_config**: UI component configuration and display settings

Configuration Structure
***********************

All workflow configurations follow this general structure:

.. code-block:: json

   {
     "orchestrator_class": "OrchestratorClassName",
     "processor_config": {
       "OpenEdXProcessor": { },
       "LLMProcessor": { }
     },
     "actuator_config": {
       "UIComponents": {
         "request": { },
         "response": { },
         "metadata": { }
       }
     }
   }

Examples
********

Anthropic Hello Example
========================

A simple workflow that uses Anthropic's Claude to respond with a greeting.

.. code-block:: json

   {
     "orchestrator_class": "DirectLLMResponse",
     "processor_config": {
       "OpenEdXProcessor": {
       },
       "LLMProcessor": {
         "function": "anthropic_hello",
         "config": "anthropic"
       }
     },
     "actuator_config": {
       "UIComponents": {
         "request": {
           "component": "AIRequestComponent",
           "config": {
             "buttonText": "Hello [config api]",
             "customMessage": "Claude will say hello [config api]"
           }
         },
         "response": {
           "component": "AIResponseComponent",
           "config": {
             "customMessage": "AI Assistant Response [config api]"
           }
         },
         "metadata": {
             "version": 0.1,
             "provider": "config_api"
         }
       }
     }
   }

**Use Case**: Testing Anthropic/Claude integration with minimal configuration.

**Key Features**:

- Uses ``DirectLLMResponse`` orchestrator for simple request-response
- Configures Anthropic as the LLM provider
- Displays a button triggering Claude to respond

OpenAI Hello Example
=====================

A simple workflow using OpenAI's ChatGPT to respond with a greeting.

.. code-block:: json

   {
     "orchestrator_class": "DirectLLMResponse",
     "processor_config": {
       "OpenEdXProcessor": {
       },
       "LLMProcessor": {
         "function": "openai_hello",
         "config": "openai"
       }
     },
     "actuator_config": {
       "UIComponents": {
         "request": {
           "component": "AIRequestComponent",
           "config": {
             "buttonText": "Ask AI [config api]",
             "customMessage": "ChatGPT will say hello [config api]"
           }
         },
         "response": {
           "component": "AIResponseComponent",
           "config": {
             "customMessage": "AI Assistant Response [config api]"
           }
         },
         "metadata": {
             "version": 0.1,
             "provider": "config_api"
         }
       }
     }
   }

**Use Case**: Testing OpenAI/ChatGPT integration with minimal configuration.

**Key Features**:

- Uses ``DirectLLMResponse`` orchestrator
- Configures OpenAI as the LLM provider
- Simple button-based UI interaction

Default Configuration (Explain Like Five)
==========================================

A workflow that retrieves course content and generates simplified explanations suitable for beginners.

.. code-block:: json

   {
     "orchestrator_class": "DirectLLMResponse",
     "processor_config": {
       "OpenEdXProcessor": {
         "function": "get_unit_content",
         "char_limit": 300
       },
       "LLMProcessor": {
         "function": "explain_like_five",
         "config": "default"
       }
     },
     "actuator_config": {
       "UIComponents": {
         "request": {
           "component": "AIRequestComponent",
           "config": {
             "buttonText": "Ask AI [config api]",
             "customMessage": "Explain me like I'm 5 [config api]"
           }
         },
         "response": {
           "component": "AIResponseComponent",
           "config": {
             "customMessage": "AI Assistant Response [config api]"
           }
         },
         "metadata": {
             "version": 0.1,
             "provider": "config_api"
         }
       }
     }
   }

**Use Case**: Providing simplified explanations of course content to learners.

**Key Features**:

- Extracts course unit content (limited to 300 characters)
- Uses ``explain_like_five`` function to generate beginner-friendly explanations
- Direct response workflow pattern

OpenAI Threads (Chat Interface)
================================

A conversational workflow that maintains chat history and provides contextual responses.

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
         "config": "openai"
       },
       "SubmissionProcessor": {
         "function": "get_chat_history",
         "max_context_messages": 3
       }
     },
     "actuator_config": {
       "UIComponents": {
         "request": {
           "component": "AIRequestComponent",
           "config": {
             "buttonText": "Open Chat",
             "customMessage": "Chat with an AI teaching assistant",
             "action": null
           }
         },
         "response": {
           "component": "AISidebarResponse",
           "config": {
             "customMessage": "AI powered assistant"
           }
         },
         "metadata": {
             "version": 0.1,
             "provider": "config_api"
         }
       }
     }
   }

**Use Case**: Interactive chat assistant that maintains conversation context.

**Key Features**:

- Uses ``ThreadedLLMResponse`` orchestrator for multi-turn conversations
- Maintains chat history
- Includes course content as context
- Sidebar UI component for chat interface

Default CMS Configuration (Educator Assistant)
===============================================

An educator-focused workflow for generating quiz questions from course content.

.. code-block:: json

   {
     "orchestrator_class": "EducatorAssistantOrchestrator",
     "processor_config": {
       "OpenEdXProcessor": {
         "function": "get_unit_content",
         "char_limit": 300
       },
       "EducatorAssistantProcessor": {
         "function": "generate_quiz_questions",
         "config": "openai"
       }
     },
     "actuator_config": {
       "UIComponents": {
         "request": {
           "component": "AIEducatorLibraryAssistComponent",
           "config": {
             "titleText": "AI Assistant",
             "buttonText": "Start",
             "customMessage": "Use an AI workflow to create multiple answer questions from this unit in a content library",
             "preloadPreviousSession": true
           }
         },
         "response": {
           "component": "AIEducatorLibraryResponseComponent",
           "config": {
             "titleText": "AI Assistant",
             "customMessage": "Assistance completed successfully",
             "hyperlinkText": "View content >"
           }
         },
         "metadata": {
             "version": 0.1,
             "provider": "config_api"
         }
       }
     }
   }

**Use Case**: Helping educators create assessment content from course units.

**Key Features**:

- Uses ``EducatorAssistantOrchestrator`` for content creation workflows
- Generates quiz questions based on unit content
- Specialized educator-focused UI components
- Session persistence support
- Designed for CMS (Studio) environment

Mock Response Example
======================

A testing configuration that returns mock responses without actual LLM calls.

.. code-block:: json

   {
     "orchestrator_class": "MockResponse",
     "processor_config": {
       "OpenEdXProcessor": {
       },
       "LLMProcessor": {
       }
     },
     "actuator_config": {
       "UIComponents": {
         "request": {
           "component": "AIRequestComponent",
           "config": {
             "buttonText": "Ask AI [config api]",
             "customMessage": "A mocked response from the server [config api]"
           }
         },
         "response": {
           "component": "AISidebarResponse",
           "config": {
             "customMessage": "AI Assistant Sidebar Response [config api]"
           }
         },
         "metadata": {
             "version": 0.1,
             "provider": "config_api"
         }
       }
     }
   }

**Use Case**: Testing UI components and workflow logic without making actual LLM API calls.

**Key Features**:

- Uses ``MockResponse`` orchestrator
- Empty processor configurations
- Useful for development and testing
- No LLM API keys required

Configuration Components
************************

Orchestrator Classes
====================

- **DirectLLMResponse**: Simple request-response pattern
- **ThreadedLLMResponse**: Multi-turn conversation with history
- **EducatorAssistantOrchestrator**: Content creation workflows for educators
- **MockResponse**: Testing orchestrator with mock responses

Processors
==========

OpenEdXProcessor
----------------

Extracts data from the Open edX platform.

Common functions:

- ``get_unit_content``: Retrieves content from a course unit

  - ``char_limit``: Maximum characters to extract

LLMProcessor
------------

Handles LLM provider interactions.

Common functions:

- ``anthropic_hello``: Claude greeting
- ``openai_hello``: ChatGPT greeting
- ``explain_like_five``: Simplified explanations
- ``chat_with_context``: Contextual chat responses
- ``generate_quiz_questions``: Question generation

Common configs:

- ``anthropic``: Use Anthropic/Claude
- ``openai``: Use OpenAI/ChatGPT
- ``default``: Default LLM configuration

SubmissionProcessor
-------------------

Manages user input and conversation history.

Common functions:

- ``get_chat_history``: Retrieve previous messages

  - ``max_context_messages``: Number of historical messages to include

UI Components
=============

Request Components
------------------

- **AIRequestComponent**: Standard button trigger
- **AIEducatorLibraryAssistComponent**: Educator-specific interface

Response Components
-------------------

- **AIResponseComponent**: Standard response display
- **AISidebarResponse**: Sidebar chat interface
- **AIEducatorLibraryResponseComponent**: Educator-specific response display

See Also
********

- :doc:`../concepts/index` - Core concepts and architecture
- :doc:`../how-tos/index` - How-to guides for common tasks
- Model reference: ``openedx_ai_extensions.workflows.models.AIWorkflowConfig``
