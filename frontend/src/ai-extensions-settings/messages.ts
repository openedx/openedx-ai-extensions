import { defineMessages } from '@edx/frontend-platform/i18n';

const messages = defineMessages({
  // Card messages
  'openedx-ai-extensions.settings-card.title': {
    id: 'openedx-ai-extensions.settings-card.title',
    defaultMessage: 'AI Extensions Settings',
    description: 'Title of the AI extensions settings card',
  },
  'openedx-ai-extensions.settings-card.description': {
    id: 'openedx-ai-extensions.settings-card.description',
    defaultMessage: 'Configure AI-powered workflows for your course.',
    description: 'Description of the AI extensions settings card',
  },
  'openedx-ai-extensions.settings-card.badge': {
    id: 'openedx-ai-extensions.settings-card.badge',
    defaultMessage: 'New',
    description: 'Badge label for new feature',
  },

  // Modal messages
  'openedx-ai-extensions.settings-modal.title': {
    id: 'openedx-ai-extensions.settings-modal.title',
    defaultMessage: 'AI Extensions Settings',
    description: 'Title of the AI extensions settings modal',
  },

  // Tab labels
  'openedx-ai-extensions.settings-modal.tab.workflows': {
    id: 'openedx-ai-extensions.settings-modal.tab.workflows',
    defaultMessage: 'Workflows Config',
    description: 'Tab label for workflows configuration',
  },

  // Workflows tab content
  'openedx-ai-extensions.settings-modal.workflows.placeholder': {
    id: 'openedx-ai-extensions.settings-modal.workflows.placeholder',
    defaultMessage: 'Workflows configuration is under development. This feature will allow you to configure AI-powered workflows for your course.',
    description: 'Placeholder text for workflows config tab',
  },

  // Profiles list
  'openedx-ai-extensions.settings-modal.workflows.profiles.title': {
    id: 'openedx-ai-extensions.settings-modal.workflows.profiles.title',
    defaultMessage: 'Available AI Profiles',
    description: 'Section title for the list of available AI profiles',
  },
  'openedx-ai-extensions.settings-modal.workflows.profiles.loading': {
    id: 'openedx-ai-extensions.settings-modal.workflows.profiles.loading',
    defaultMessage: 'Loading profiles...',
    description: 'Loading message while fetching AI profiles',
  },
  'openedx-ai-extensions.settings-modal.workflows.profiles.empty': {
    id: 'openedx-ai-extensions.settings-modal.workflows.profiles.empty',
    defaultMessage: 'No AI profiles are configured for this course.',
    description: 'Message shown when no profiles are found for the course',
  },
  'openedx-ai-extensions.settings-modal.workflows.profiles.error': {
    id: 'openedx-ai-extensions.settings-modal.workflows.profiles.error',
    defaultMessage: 'Failed to load profiles. Please try again.',
    description: 'Error message shown when the profiles list request fails',
  },
  'openedx-ai-extensions.settings-modal.workflows.profiles.config-label': {
    id: 'openedx-ai-extensions.settings-modal.workflows.profiles.config-label',
    defaultMessage: 'Configuration',
    description: 'Label for the effective configuration section of a profile card',
  },
});

export default messages;
