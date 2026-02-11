import { defineMessages } from '@edx/frontend-platform/i18n';

const messages = defineMessages({
  'ai.extensions.config.alert.heading': {
    id: 'ai.extensions.config.alert.heading',
    defaultMessage: 'Configuration Error',
    description: 'Heading for alert when AI extensions configuration fails to load',
  },
  'ai.extensions.config.alert.message': {
    id: 'ai.extensions.config.alert.message',
    defaultMessage: 'Failed to load AI extensions configuration: {error}',
    description: 'Message for alert when AI extensions configuration fails to load, with error details',
  },
  'ai.extensions.config.invalid.heading': {
    id: 'ai.extensions.config.invalid.heading',
    defaultMessage: 'Invalid Configuration',
    description: 'Heading for alert when configuration is invalid',
  },
  'ai.extensions.config.missing.request': {
    id: 'ai.extensions.config.missing.request',
    defaultMessage: 'Request component configuration is missing.',
    description: 'Error message when request component config is missing',
  },
  'ai.extensions.config.missing.response': {
    id: 'ai.extensions.config.missing.response',
    defaultMessage: 'Response component configuration is missing.',
    description: 'Error message when response component config is missing',
  },
  'ai.extensions.config.unknown.heading': {
    id: 'ai.extensions.config.unknown.heading',
    defaultMessage: 'Unknown Component',
    description: 'Heading for alert when a component is unknown',
  },
  'ai.extensions.config.unknown.request': {
    id: 'ai.extensions.config.unknown.request',
    defaultMessage: 'Request component "{componentName}" is not available.',
    description: 'Error message when request component is not found',
  },
  'ai.extensions.config.unknown.response': {
    id: 'ai.extensions.config.unknown.response',
    defaultMessage: 'Response component "{componentName}" is not available.',
    description: 'Error message when response component is not found',
  },
  'ai.extensions.config.available.components': {
    id: 'ai.extensions.config.available.components',
    defaultMessage: 'Available components: {components}',
    description: 'List of available components',
  },
  'ai.extensions.config.fallback.error': {
    id: 'ai.extensions.config.fallback.error',
    defaultMessage: 'Using fallback configuration due to error: {error}',
    description: 'Warning message when using fallback configuration',
  },
  // Request Component Messages
  'ai.extensions.request.analyzing': {
    id: 'ai.extensions.request.analyzing',
    defaultMessage: 'Analyzing content...',
    description: 'Message shown when AI is analyzing content',
  },
  'ai.extensions.request.default.message': {
    id: 'ai.extensions.request.default.message',
    defaultMessage: 'Get personalized AI assistance for this learning unit',
    description: 'Default help message in the request component',
  },
  'ai.extensions.request.default.button': {
    id: 'ai.extensions.request.default.button',
    defaultMessage: 'Ask AI',
    description: 'Default button text in the request component',
  },
  // Response Component Messages
  'ai.extensions.response.default.title': {
    id: 'ai.extensions.response.default.title',
    defaultMessage: 'AI Assistant Response',
    description: 'Default title for the AI response component',
  },
  'ai.extensions.response.clear': {
    id: 'ai.extensions.response.clear',
    defaultMessage: 'Clear',
    description: 'Text for the clear button in the response component',
  },
  // Sidebar Messages
  'ai.extensions.sidebar.aria.label': {
    id: 'ai.extensions.sidebar.aria.label',
    defaultMessage: 'AI Assistant Chat',
    description: 'Aria label for the AI assistant chatbot sidebar',
  },
  'ai.extensions.sidebar.close.label': {
    id: 'ai.extensions.sidebar.close.label',
    defaultMessage: 'Close AI Assistant',
    description: 'Label for button that closes the AI sidebar',
  },
  'ai.extensions.sidebar.input.label': {
    id: 'ai.extensions.sidebar.input.label',
    defaultMessage: 'Type your question here',
    description: 'Label for the text input where users type their questions to the AI',
  },
  'ai.extensions.sidebar.send.label': {
    id: 'ai.extensions.sidebar.send.label',
    defaultMessage: 'Send message',
    description: 'Label for the button that sends the user message to the AI',
  },
  'ai.extensions.sidebar.loading.history': {
    id: 'ai.extensions.sidebar.loading.history',
    defaultMessage: 'Loading previous messages...',
    description: 'Status message announced to screen readers when chat history is loading',
  },
  'ai.extensions.sidebar.thinking': {
    id: 'ai.extensions.sidebar.thinking',
    defaultMessage: 'AI is thinking...',
    description: 'Status message announced to screen readers when AI is generating a response',
  },
  'ai.extensions.sidebar.clear.chat': {
    id: 'ai.extensions.sidebar.clear.chat',
    defaultMessage: 'Clear Chat',
    description: 'Text for clearing chat in the sidebar settings dropdown',
  },
  'ai.extensions.sidebar.load.older': {
    id: 'ai.extensions.sidebar.load.older',
    defaultMessage: 'Load older messages ↑',
    description: 'Text for loading older messages in the sidebar',
  },
  'ai.extensions.sidebar.default.title': {
    id: 'ai.extensions.sidebar.default.title',
    defaultMessage: 'AI Assistant Response',
    description: 'Default title in the sidebar header',
  },
  // Educator Library Assist Messages
  'ai.extensions.educator.title': {
    id: 'ai.extensions.educator.title',
    defaultMessage: 'AI Assistant',
    description: 'Title for the educator AI library assist component',
  },
  'ai.extensions.educator.start': {
    id: 'ai.extensions.educator.start',
    defaultMessage: 'Start',
    description: 'Default button text to start the educator AI workflow',
  },
  'ai.extensions.educator.default.message': {
    id: 'ai.extensions.educator.default.message',
    defaultMessage: 'Use an AI workflow to create multiple answer questions from this unit in a content library',
    description: 'Default descriptive message for educator library assist',
  },
  'ai.extensions.educator.error.questions': {
    id: 'ai.extensions.educator.error.questions',
    defaultMessage: 'Failed to generate questions. Please try again.',
    description: 'Error message when question generation fails',
  },
  'ai.extensions.educator.cancel': {
    id: 'ai.extensions.educator.cancel',
    defaultMessage: 'Cancel',
    description: 'Text for the cancel button',
  },
  'ai.extensions.educator.library.label': {
    id: 'ai.extensions.educator.library.label',
    defaultMessage: 'Library',
    description: 'Label for library selection field',
  },
  'ai.extensions.educator.library.loading': {
    id: 'ai.extensions.educator.library.loading',
    defaultMessage: 'Loading libraries...',
    description: 'Status message while fetching libraries',
  },
  'ai.extensions.educator.library.select': {
    id: 'ai.extensions.educator.library.select',
    defaultMessage: 'Select a library...',
    description: 'Placeholder for library selection',
  },
  'ai.extensions.educator.library.none': {
    id: 'ai.extensions.educator.library.none',
    defaultMessage: 'No libraries available',
    description: 'Message when no libraries are found',
  },
  'ai.extensions.educator.library.help.loading': {
    id: 'ai.extensions.educator.library.help.loading',
    defaultMessage: 'Loading available libraries...',
    description: 'Help text while loading libraries',
  },
  'ai.extensions.educator.library.help.select': {
    id: 'ai.extensions.educator.library.help.select',
    defaultMessage: 'Select the library where questions will be added',
    description: 'Help text for library selection',
  },
  'ai.extensions.educator.questions.label': {
    id: 'ai.extensions.educator.questions.label',
    defaultMessage: 'Number of Questions',
    description: 'Label for number of questions field',
  },
  'ai.extensions.educator.questions.help': {
    id: 'ai.extensions.educator.questions.help',
    defaultMessage: 'Number of questions to generate (1-50)',
    description: 'Help text for number of questions',
  },
  'ai.extensions.educator.instructions.label': {
    id: 'ai.extensions.educator.instructions.label',
    defaultMessage: 'Additional Instructions (Optional)',
    description: 'Label for additional instructions field',
  },
  'ai.extensions.educator.instructions.placeholder': {
    id: 'ai.extensions.educator.instructions.placeholder',
    defaultMessage: 'Add any specific instructions for the AI...',
    description: 'Placeholder for additional instructions field',
  },
  'ai.extensions.educator.instructions.help': {
    id: 'ai.extensions.educator.instructions.help',
    defaultMessage: 'Provide additional context or instructions for question generation',
    description: 'Help text for additional instructions',
  },
  'ai.extensions.educator.generating': {
    id: 'ai.extensions.educator.generating',
    defaultMessage: 'Generating...',
    description: 'Loading text during question generation',
  },
  'ai.extensions.educator.generate.button': {
    id: 'ai.extensions.educator.generate.button',
    defaultMessage: 'Generate Questions',
    description: 'Button text to submit the question generation form',
  },
  // Educator Response Messages
  'ai.extensions.educator.success.message': {
    id: 'ai.extensions.educator.success.message',
    defaultMessage: 'Question generation success.',
    description: 'Success message after generating questions',
  },
  'ai.extensions.educator.hyperlink.text': {
    id: 'ai.extensions.educator.hyperlink.text',
    defaultMessage: 'View content',
    description: 'Text for the link to view generated content',
  },
  'ai.extensions.educator.task.completed': {
    id: 'ai.extensions.educator.task.completed',
    defaultMessage: 'Task completed successfully',
    description: 'Message when async task completes',
  },
  'ai.extensions.educator.task.failed': {
    id: 'ai.extensions.educator.task.failed',
    defaultMessage: 'Task failed',
    description: 'Message when async task fails',
  },
  'ai.extensions.educator.task.processing': {
    id: 'ai.extensions.educator.task.processing',
    defaultMessage: 'Processing your request...',
    description: 'Message while async task is processing',
  },
  'ai.extensions.educator.task.timeout': {
    id: 'ai.extensions.educator.task.timeout',
    defaultMessage: 'Task is taking longer than expected. Please check back later.',
    description: 'Message when async task takes too long',
  },
  'ai.extensions.educator.processing': {
    id: 'ai.extensions.educator.processing',
    defaultMessage: 'Processing',
    description: 'General processing label',
  },
  'ai.extensions.educator.last.updated': {
    id: 'ai.extensions.educator.last.updated',
    defaultMessage: 'Last updated: {time}',
    description: 'Timestamp of last status update',
  },
  'ai.extensions.educator.update.button': {
    id: 'ai.extensions.educator.update.button',
    defaultMessage: 'Update',
    description: 'Text for manual status update button',
  },
  'ai.extensions.educator.success.text': {
    id: 'ai.extensions.educator.success.text',
    defaultMessage: 'The generated questions have been added to your Content Library. {br} They are saved in an unpublished state for you to review before making them available to learners.',
    description: 'Detailed success message about content being added and ready for review',
  },
  // General Button Plugin Messages
  'ai.extensions.button.default.message': {
    id: 'ai.extensions.button.default.message',
    defaultMessage: 'Need help understanding this content?',
    description: 'Default help message for the simple AI button',
  },
  'ai.extensions.button.default.text': {
    id: 'ai.extensions.button.default.text',
    defaultMessage: 'Get AI Assistance',
    description: 'Default text for the simple AI button',
  },
  'ai.extensions.button.workflow.fallback': {
    id: 'ai.extensions.button.workflow.fallback',
    defaultMessage: 'Provide learning assistance for this content',
    description: 'Fallback message sent to AI if none provided',
  },
});

export default messages;
