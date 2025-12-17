"""Constants for AI workflow xAPI transformers."""

# xAPI verbs
XAPI_VERB_INITIALIZED = "http://adlnet.gov/expapi/verbs/initialized"
XAPI_VERB_INTERACTED = "http://adlnet.gov/expapi/verbs/interacted"
XAPI_VERB_COMPLETED = "http://adlnet.gov/expapi/verbs/completed"

# Display names
INITIALIZED = "initialized"
INTERACTED = "interacted"
COMPLETED = "completed"

# Languages
EN = "en"

# xAPI activity types
# Custom activity type for AI-powered educational workflows
# Following the Open edX xAPI pattern: https://w3id.org/xapi/openedx/activity/*
XAPI_ACTIVITY_AI_WORKFLOW = "https://w3id.org/xapi/openedx/activity/ai-workflow"

# xAPI extensions
XAPI_EXTENSION_WORKFLOW_ACTION = "https://w3id.org/xapi/openedx/extension/ai-workflow-action"
XAPI_EXTENSION_PROMPT_TEMPLATE_SLUG = "https://w3id.org/xapi/openedx/extension/prompt-template-slug"
XAPI_EXTENSION_LOCATION_ID = "https://w3id.org/xapi/openedx/extension/location-id"

# Event names
EVENT_NAME_WORKFLOW_INITIALIZED = "openedx.ai.workflow.initialized"
EVENT_NAME_WORKFLOW_INTERACTED = "openedx.ai.workflow.interacted"
EVENT_NAME_WORKFLOW_COMPLETED = "openedx.ai.workflow.completed"

# All events list - useful for iteration in settings and configuration
ALL_EVENTS = [
    EVENT_NAME_WORKFLOW_INITIALIZED,
    EVENT_NAME_WORKFLOW_INTERACTED,
    EVENT_NAME_WORKFLOW_COMPLETED,
]
