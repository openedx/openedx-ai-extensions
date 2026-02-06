.. _qs-usage:

Usage Guide
###########

This guide walks you through creating your first AI workflows and configuring them for different contexts in your Open edX installation.

.. note::

   This guide assumes the reader has access to the Django Admin interface for their Open edX site.

.. contents::
 :local:
 :depth: 1

Prerequisites
*************

Before following this guide, ensure you have:

- Completed the :ref:`plugin installation <readme>`
- Configured at least one AI provider (see :ref:`qs config`)
- Django admin access to your Open edX instance

Overview
********

To make an AI workflow available to users, you need to create two components:

1. **Profile**: Defines what the AI will do (the behavior and instructions)
2. **Scope**: Defines where the AI workflow will appear (LMS/Studio, courses, specific locations)

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

3. Click :guilabel:`Save and continue editing`

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
   - **Course ID**: Leave empty (applies to all courses), or :ref:`target specific courses <target-specific-courses>`
   - **Location regex**: Leave empty (applies to all units), or :ref:`target specific units <target-specific-units>`
   - **Profile**: Select the profile you just created using the name you chose in the **Slug** field

3. Click :guilabel:`Save`

Testing the Workflow
=====================

Navigate to any course unit in the LMS. You should see the AI workflow interface available to learners.

.. image:: /_static/screenshots/lms_summary_workflow_1.png
   :alt: Content summary workflow in LMS unit view

.. image:: /_static/screenshots/lms_summary_workflow_2.png
   :alt: Response of the summary workflow in LMS

Studio Example: Library Question Assistant
*******************************************

This example creates an AI assistant for content authors working with courses in Studio.

When viewed from a specific unit in a course, this assistant allows content authors to use an AI workflow to create multiple answer questions from the context of the viewed unit. Created problems are stored in a content library.

Creating the Profile
====================

1. Navigate to the profile creation page:

   .. code-block:: text

      /admin/openedx_ai_extensions/aiworkflowprofile/add/

2. Configure the profile:

   - **Slug**: Enter a descriptive identifier (e.g., ``studio-library-assistant``)
   - **Base filepath**: Select ``base.library_questions_assistant``

3. Click :guilabel:`Save and continue editing`

4. Review the base template and effective configuration as before.

Creating the Scope
===================

1. Navigate to the scope creation page:

   .. code-block:: text

      /admin/openedx_ai_extensions/aiworkflowscope/add/

2. Configure the scope:

   - **Service variant**: Select ``CMS - Studio``
   - **Course ID**: Leave empty (applies to all courses in Studio), or :ref:`target specific courses <target-specific-courses>`
   - **Location regex**: Leave empty - there is no targeting locations in the Studio context
   - **Profile**: Select the profile you just created

3. Click :guilabel:`Save`

Testing the Workflow
=====================

Navigate to a course in Studio. You should see the AI assistant interface available to authors in the right sidebar of the Studio course.

.. image:: /_static/screenshots/studio_library_assistant.png
   :alt: Library question assistant in Studio

Advanced Configuration
**********************

.. _target-specific-courses:

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
2. Set **Course ID** to: ``course-v1:OpenedX+DemoX+Demo_Course``
3. Save the scope

.. note::
   Multiple courses are not currently supported in a single scope. Create separate scopes for different courses.

.. _target-specific-units:

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

   .*30b3cb3f372a493589a9632c472550a7

This matches any location ending with that block ID.

Targeting Multiple Units
------------------------

To target multiple specific units, use the OR operator (``|``):

.. code-block:: text

   .*(a3ada3c77ab74014aa620f3c494e5558|30b3cb3f372a493589a9632c472550a7|7f8e9d6c5b4a3210fedcba9876543210)

This matches any unit with one of the three specified block IDs.

.. warning::
   Location regex is a powerful but technical feature. Test your regex patterns carefully to ensure they match the intended units.

Next Steps
**********

Now that you have basic workflows configured, you can:

- Experiment with different base profiles such as the chat for different providers
- Create :ref:`custom prompts tailored to your use cases <Customizing Prompts>`
- Configure multiple scopes for different courses and contexts
- Monitor usage and refine your configurations

For advanced customization and development, see the how-to guides and reference documentation.
For additional support, visit the `GitHub Issues <https://github.com/openedx/openedx-ai-extensions/issues>`_ page.

.. seealso::

   :ref:`qs config`

   :ref:`Customizing Prompts`