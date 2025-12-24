Usage Guide
###########

This guide walks you through creating your first AI workflows and configuring them for different contexts in your Open edX installation.

Prerequisites
*************

Before following this guide, ensure you have:

- Completed the plugin installation
- Configured at least one AI provider (see `Configuration Guide <configuration_guide.html>`_)
- Django admin access to your Open edX instance

Overview
********

To make an AI workflow available to users, you need to create two components:

1. **Profile**: Defines what the AI will do (the behavior and instructions)
2. **Scope**: Defines where the AI workflow will appear (LMS/CMS, courses, specific locations)

LMS Example: Content Summary
*****************************

This example creates a content summarization feature available to learners in the LMS.

Creating the Profile
====================

1. Navigate to the profile creation page:

   .. code-block:: text

      /admin/openedx_ai_extensions/aiworkflowprofile/add/

   .. image:: /_static/screenshots/profile_create.png
      :alt: Create new profile interface

2. Configure the profile:

   - **Slug**: Enter a descriptive identifier (e.g., ``lms-content-summary``)
   - **Base filepath**: Select ``base.summary`` from the dropdown

3. Click **Save and continue editing**

4. Review the configuration:

   You can now see two sections:

   - **Base template**: The default configuration from the selected filepath
   - **Effective configuration**: The final configuration after applying any patches

   .. image:: /_static/screenshots/profile_configuration_view.png
      :alt: Profile configuration view showing base template and effective configuration

Creating the Scope
===================

1. Navigate to the scope creation page:

   .. code-block:: text

      /admin/openedx_ai_extensions/aiworkflowscope/add/

   .. image:: /_static/screenshots/scope_create.png
      :alt: Create new scope interface

2. Configure the scope:

   - **Service variant**: Select ``LMS``
   - **Course ID**: Leave empty (applies to all courses)
   - **Location regex**: Leave empty (applies to all units)
   - **Profile**: Select the profile you just created

3. Click **Save**

Testing the Workflow
=====================

Navigate to any course unit in the LMS. You should see the AI workflow interface available to learners.

.. image:: /_static/screenshots/lms_summary_workflow_1.png
   :alt: Content summary workflow in LMS unit view

.. image:: /_static/screenshots/lms_summary_workflow_2.png
   :alt: Response of the summary workflow in LMS

Studio Example: Library Question Assistant
*******************************************

This example creates an AI assistant for content authors working with content libraries in Studio.

Creating the Profile
====================

1. Navigate to the profile creation page:

   .. code-block:: text

      /admin/openedx_ai_extensions/aiworkflowprofile/add/

2. Configure the profile:

   - **Slug**: Enter a descriptive identifier (e.g., ``studio-library-assistant``)
   - **Base filepath**: Select ``base.library_questions_assistant``

3. Click **Save and continue editing**

4. Review the base template and effective configuration as before.

Creating the Scope
===================

1. Navigate to the scope creation page:

   .. code-block:: text

      /admin/openedx_ai_extensions/aiworkflowscope/add/

2. Configure the scope:

   - **Service variant**: Select ``CMS - Studio``
   - **Course ID**: Leave empty (applies to all content libraries)
   - **Location regex**: Leave empty (applies to all locations)
   - **Profile**: Select the profile you just created

3. Click **Save**

Testing the Workflow
=====================

Navigate to a content library in Studio. You should see the AI assistant interface available to authors.

.. image:: /_static/screenshots/studio_library_assistant.png
   :alt: Library question assistant in Studio

Advanced Configuration
**********************

Targeting Specific Courses
===========================

To limit a workflow to a specific course, use the **Course ID** field in the scope configuration.

Course ID Format
----------------

Course IDs follow this format:

.. code-block:: text

   course-v1:edunext+01+2025

Example: To make a workflow available only in your Demo course:

1. Edit your scope configuration
2. Set **Course ID** to: ``course-v1:edX+DemoX+Demo_Course``
3. Save the scope

.. note::
   Multiple courses are not currently supported in a single scope. Create separate scopes for different courses.

Targeting Specific Units
=========================

The **Location regex** field allows you to target specific course units using regular expressions.

Unit Location Format
--------------------

Course units have location IDs in this format:

.. code-block:: text

   block-v1:edX+DemoX+Demo_Course+type@vertical+block@30b3cb3f372a493589a9632c472550a7

Targeting a Single Unit
-----------------------

To target a specific unit, use a regex pattern matching the block ID:

.. code-block:: text

   .*a3ada3c77ab74014aa620f3c494e5558

This matches any location ending with that block ID.

Targeting Multiple Units
------------------------

To target multiple specific units, use the OR operator (``|``):

.. code-block:: text

   .*(a3ada3c77ab74014aa620f3c494e5558|30b3cb3f372a493589a9632c472550a7|7f8e9d6c5b4a3210fedcba9876543210)

This matches any unit with one of the three specified block IDs.

.. warning::
   Location regex is a powerful but technical feature. Test your regex patterns carefully to ensure they match the intended units.

Customizing Prompts
*******************

You can customize the AI's instructions and behavior by modifying prompts at the profile level.

Method 1: Inline Prompt in Profile Patch
=========================================

Use the **Content patch** field to override the prompt:

Single Line Prompt
------------------

.. code-block:: json

   {
     "processor_config": {
       "LLMProcessor": {
         "prompt": "Your custom prompt here"
       }
     }
   }

Multi-line Prompt
-----------------

For longer prompts, use the backslash line continuation syntax:

.. code-block:: json

   {
     "processor_config": {
       "LLMProcessor": {
         "prompt": "\
   Your custom prompt \
   on many lines \
   with detailed instructions \
   "
       }
     }
   }

Example Profile
---------------

The plugin includes an example at ``base.custom_prompt`` demonstrating this approach.

.. image:: /_static/screenshots/inline_prompt_patch.png
   :alt: Inline prompt configuration in profile patch

Method 2: Prompt Templates (Recommended)
=========================================

For reusable prompts, create a prompt template that can be referenced by multiple profiles.

Creating a Prompt Template
---------------------------

1. Navigate to the prompt template creation page:

   .. code-block:: text

      /admin/openedx_ai_extensions/prompttemplate/add/

2. Configure the template:

   - **Slug**: Enter a descriptive identifier (e.g., ``tutor-assistant-prompt``)
   - **Prompt body**: Enter your prompt text

3. Click **Save**

4. Note the identifiers shown after saving:

   .. code-block:: text

      "prompt_template": "769965eb-c242-4512-8d27-4f4feb800fe2"
      "prompt_template": "your-prompt-slug"

   You can use either the UUID or the slug to reference this template.

Using a Prompt Template in a Profile
-------------------------------------

In your profile's **Content patch** field:

.. code-block:: json

   {
     "processor_config": {
       "LLMProcessor": {
         "prompt_template": "769965eb-c242-4512-8d27-4f4feb800fe2"
       }
     }
   }

Or using the slug:

.. code-block:: json

   {
     "processor_config": {
       "LLMProcessor": {
         "prompt_template": "tutor-assistant-prompt"
       }
     }
   }

.. tip::
   Using prompt templates makes it easier to:

   - Reuse prompts across multiple profiles
   - Update prompts without modifying profile configurations
   - Maintain a library of tested, effective prompts

Next Steps
**********

Now that you have basic workflows configured, you can:

- Experiment with different base profiles such as the chat for different providers
- Create custom prompts tailored to your use cases
- Configure multiple scopes for different courses and contexts
- Monitor usage and refine your configurations

For advanced customization and development, see the how-to guides and reference documentation.
For additional support, visit the `GitHub Issues <https://github.com/openedx/openedx-ai-extensions/issues>`_ page.
