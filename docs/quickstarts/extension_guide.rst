.. _qs-extension:

Extension Guide
===============

This guide provides a quickstart for developers who want to extend the Open edX AI infrastructure by creating custom plugins. We use the **openedx-ai-badges** project as a reference implementation.

.. note::

   This guide assumes you are familiar with Open edX plugin development and have a local Tutor environment set up.

.. contents::
 :local:
 :depth: 1

Overview
********

The AI framework is designed to be extensible. Instead of modifying the core, you can create a standalone plugin that registers new behaviors. A complete plugin typically extends three areas: backend, frontend, and tutor configuration.

Project Structure
*****************

A standard AI extension repository follows a modular layout designed to integrate with both the Open edX backend and the Micro-Frontend (MFE) architecture. While the reference implementation (``openedx-ai-badges``) includes all layers, the structure is adaptable to your specific needs:

* **``backend/``**: The Django application containing custom **processors, orchestrators, and profiles**.
* **``frontend/``**: React components, UI slots, and styles for MFE integration.
* **``tutor/``**: The Tutor plugin files required for environment configuration and automated deployment.

.. note::
   **Modular Flexibility**: You do not need to implement all three components. For example, if your feature only requires a new data transformation logic, you might only need the ``backend/`` directory. Similarly, a plugin might only provide a specialized UI for existing core logic. The framework allows you to mix and match components based on the specific requirements of your AI workflow.

Backend Implementation
**********************

The backend logic of an AI plugin is primarily driven by the **Workflow Profile**. The framework uses these JSON blueprints to dynamically discover and load your custom logic.

1. Define the Workflow Profile
==============================

The **Profile** is a JSON file that acts as the blueprint for your feature. It maps orchestrators, processors, and UI components into a single configuration.

Create your profile (e.g., ``workflows/profiles/badges_base.json``):

.. code-block:: json

   {
     "orchestrator_class": "openedx_ai_badges.workflows.orchestrators.BadgeOrchestrator",
     "processor_config": {
         "BadgeProcessor": {
             "function": "generate_badgeclass",
             "provider": "openai"
         }
     },
     "actuator_config": {
       "UIComponents": {
         "request": {
           "component": "AIRequestBadgesComponent",
           "config": {
             "buttonText": "Generate Badge"
           }
         }
       }
     }
   }

2. Register Profiles in Settings
================================

For the framework to discover your JSON profiles, you must add your plugin's directory to the ``WORKFLOW_TEMPLATE_DIRS`` setting.

In your plugin's settings (e.g., ``settings/common.py``):

.. code-block:: python

   def plugin_settings(settings):
       if not hasattr(settings, "WORKFLOW_TEMPLATE_DIRS"):
           settings.WORKFLOW_TEMPLATE_DIRS = []

       # Add the path to your plugin's profiles
       badges_workflow_dir = BASE_DIR / "workflows" / "profiles"
       if badges_workflow_dir not in settings.WORKFLOW_TEMPLATE_DIRS:
           settings.WORKFLOW_TEMPLATE_DIRS.append(badges_workflow_dir)

3. Plugin Configuration (apps.py)
================================

Ensure your plugin is correctly registered in Open edX so that the settings above are processed:

.. code-block:: python

   from django.apps import AppConfig
   from edx_django_utils.plugins.constants import PluginSettings

   class YourPluginConfig(AppConfig):
       name = "your_plugin_name"

       plugin_app = {
           PluginSettings.CONFIG: {
               "lms.djangoapp": { "common": { "relative_path": "settings.common" } },
               "cms.djangoapp": { "common": { "relative_path": "settings.common" } },
           },
       }

4. Implement a Custom Orchestrator
==================================

The ``orchestrator_class`` in your Profile JSON uses a full Python path to locate and instantiate your logic. By inheriting from core classes like ``SessionBasedOrchestrator``, you can customize the workflow execution.

.. code-block:: python

   # openedx_ai_badges/workflows/orchestrators.py
   from openedx_ai_extensions.orchestrators import SessionBasedOrchestrator

   class BadgeOrchestrator(SessionBasedOrchestrator):
       """
       Custom orchestrator that manages the badge generation sequence.
       """
       def run(self, input_data):
           # Your custom flow logic here
            return {
                "response": badge_data,
                "status": "completed",
            }

5. Processor Configuration Mapping
==================================

For an Orchestrator to use one or more Processors, they must be declared in the ``processor_config`` section of the Profile JSON. This mapping connects the logic with specific AI providers and functions.

.. code-block:: json

   "processor_config": {
       "BadgeProcessor": {
           "function": "generate_badgeclass",
           "provider": "openai"
       }
   }

Within your Orchestrator logic, you can then retrieve and use these processors:

.. code-block:: python

   def run(self, input_data):
       # Retrieve the processor as configured in the JSON profile
       badge_processor = BadgeProcessor(self.profile.processor_config)
       llm_result = badge_processor.process(context=str(course_context))
       badge = json.loads(llm_result.get("response", "{}"))
       # ... continue workflow

.. note::
    The process function will call the function defined in the ``processor_config``.

.. note::
    For practical examples of how to implement and combine orchestrators and processors, refer to:
    
    * `openedx-ai-extensions <https://github.com/openedx/openedx-ai-extensions>`_: For core base classes and standard implementations.
    * `openedx-ai-badges <https://github.com/edunext/openedx-ai-badges>`_: For a complete reference of a custom, multi-step workflow.

Frontend Implementation
***********************

The frontend integration is governed by a central **Extension Registry**. There are two primary ways to implement your plugin's user interface, depending on whether you want the core framework to manage the execution flow or you prefer to handle it manually.

Pattern A: Using ConfigurableAIAssistance
==========================================

This is the recommended pattern for standard AI interactions. The core provides a component called ``ConfigurableAIAssistance`` that acts as a dynamic frontend orchestrator.

* **How it works**: At runtime, this component fetches the configuration from the backend (based on the **AI Profile**). It looks for the component names defined in the profile's ``actuator_config`` and resolves them using the frontend registry.
* **Backend Control**: The backend dictates which components to render for the "request" and "response" phases by sending their registered names in the API response.

Pattern B: Independent Custom Components
=========================================

Use this pattern if you want to manage the UI and the service calls yourself, bypassing the core's automated flow. This is useful for complex features where the UI needs to do more than just a simple request/response.

* **How it works**: You create a component that calls the AI services directly using the utilities provided by the core library.
* **Why the Profile is still required**: Even if you manage the UI manually, the **Backend** still requires a Profile to identify the correct ``orchestrator_class`` and ``processor_config`` when your component triggers the workflow API.

6. Implementing UI Components
=============================

Create your React components in the ``frontend/src/components`` directory. 

**Example for Pattern A (Managed by Core):**
Your component will receives params from the Profile JSON.

.. code-block:: typescript

   // frontend/src/components/MyRequestComponent.tsx

   const MyRequestComponent = ({ customMessage, buttonText, isLoading }) => (
       <div className="ai-request-wrapper">
           {customMessage}
           <button onClick={onAskAI} disabled={isLoading}>
               {buttonText}
           </button>
       </div>
   );

   export default MyRequestComponent;

**Example for Pattern B (Manually Managed):**
Your component uses core services to build context and call the backend.

.. code-block:: typescript

   // frontend/src/components/MyIndependentTabComponent.tsx
   import { services } from '@openedx/openedx-ai-extensions-ui';

   const MyIndependentTabComponent = ({ uiSlotSelectorId, courseId, locationId }) => {
     const handleAction = async () => {
       const context = services.prepareContextData({ uiSlotSelectorId, courseId, locationId });
       const response = await services.callWorkflowService(context);
       // Handle custom UI behavior with the response
     };

     return <button onClick={handleAction}>Custom Action</button>;
   };

7. Component Registration
=========================

The ``@openedx/openedx-ai-extensions-ui`` package maintains a registry that maps strings to React components. For **Pattern A**, the name registered here **must match** the name used in the Profile JSON.

In your ``frontend/src/index.tsx`` (or your plugin's entry point):

.. code-block:: typescript

   import { registerComponents } from '@openedx/openedx-ai-extensions-ui';
   import MyRequestComponent from './components/MyRequestComponent';
   import MyIndependentTabComponent from './components/MyIndependentTabComponent';

   // Register a single component by name (Pattern A)
   registerComponents('MyRequestComponent', MyRequestComponent);

   // Register a specialized entry (e.g., a new tab in AI Settings)
   registerComponents('settings', { 
       id: 'my-plugin-id', 
       label: 'My AI Plugin', 
       component: MyIndependentTabComponent 
   });

   export { MyRequestComponent, MyIndependentTabComponent };

.. note::
   If the backend returns a component name that is not found in the registry, ``ConfigurableAIAssistance`` will display a debug alert listing all currently registered components.

Activation and Usage
********************

After implementing the backend logic, defining the Profile JSON, and registering your frontend components:

1. **Deploy**: Install your plugin in your Open edX environment.
2. **Configure Profile**: In Django Admin, create an **AI Workflow Profile** and select your JSON file as the **Base filepath**.
3. **Set Scope**: Create an **AI Workflow Scope** to map your profile to the LMS or Studio, as explained in the :ref:`qs-usage`.

Next Steps
**********

* Review the `openedx-ai-badges <https://github.com/openedx/openedx-ai-badges>`_ repository for a full working example.

.. seealso::

   :ref:`qs-usage`
   :ref:`qs-config`
