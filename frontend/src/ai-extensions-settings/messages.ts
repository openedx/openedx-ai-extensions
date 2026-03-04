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
});

export default messages;
