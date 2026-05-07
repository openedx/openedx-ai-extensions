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
    defaultMessage: 'Failed to load profiles. Please check your permissions and try again.',
    description: 'Error message shown when the profiles list request fails',
  },
  'openedx-ai-extensions.settings-modal.workflows.profiles.config-label': {
    id: 'openedx-ai-extensions.settings-modal.workflows.profiles.config-label',
    defaultMessage: 'Configuration',
    description: 'Label for the effective configuration section of a profile card',
  },

  // Profile detail view tab labels
  'openedx-ai-extensions.settings-modal.workflows.view.profile': {
    id: 'openedx-ai-extensions.settings-modal.workflows.view.profile',
    defaultMessage: 'Profile',
    description: 'Tab label for the profile configuration view',
  },
  'openedx-ai-extensions.settings-modal.workflows.view.scopes': {
    id: 'openedx-ai-extensions.settings-modal.workflows.view.scopes',
    defaultMessage: 'Scopes',
    description: 'Tab label for the profile scopes view',
  },
  'openedx-ai-extensions.settings-modal.workflows.view.prompt': {
    id: 'openedx-ai-extensions.settings-modal.workflows.view.prompt',
    defaultMessage: 'Prompt',
    description: 'Tab label for the prompt template editor view',
  },

  // Prompt template editor
  'openedx-ai-extensions.settings-modal.workflows.prompt.loading': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.loading',
    defaultMessage: 'Loading prompt…',
    description: 'Loading message while fetching the prompt template',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.created-label': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.created-label',
    defaultMessage: 'Created',
    description: 'Label for the prompt template creation date',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.updated-label': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.updated-label',
    defaultMessage: 'Updated',
    description: 'Label for the prompt template last-updated date',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.body-label': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.body-label',
    defaultMessage: 'Prompt body',
    description: 'Label for the prompt body textarea',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.save': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.save',
    defaultMessage: 'Save',
    description: 'Label for the save button in the prompt editor',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.saving': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.saving',
    defaultMessage: 'Saving…',
    description: 'Label shown on the save button while the save request is in flight',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.saved': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.saved',
    defaultMessage: 'Saved!',
    description: 'Confirmation message shown briefly after a successful save',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.save-error': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.save-error',
    defaultMessage: 'Failed to save prompt. Please try again.',
    description: 'Error message shown when the save request fails',
  },

  // Confirmation modal for saving a shared prompt template
  'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-title': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-title',
    defaultMessage: 'Save shared prompt?',
    description: 'Title of the confirmation modal shown before saving a prompt used by multiple profiles',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-body': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-body',
    defaultMessage: 'This prompt is used by {count, plural, one {1 profile} other {{count} profiles}}. Saving will affect all of them.',
    description: 'Body of the confirmation modal shown before saving a shared prompt template',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-cancel': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-cancel',
    defaultMessage: 'Cancel',
    description: 'Cancel button label in the shared-prompt save confirmation modal',
  },
  'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-confirm': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.confirm-save-confirm',
    defaultMessage: 'Save anyway',
    description: 'Confirm button label in the shared-prompt save confirmation modal',
  },

  // Usage counts
  'openedx-ai-extensions.settings-modal.workflows.prompt.usage-profiles': {
    id: 'openedx-ai-extensions.settings-modal.workflows.prompt.usage-profiles',
    defaultMessage: 'Used by {count, plural, one {1 profile} other {{count} profiles}}',
    description: 'Badge showing how many AI workflow profiles reference this prompt template',
  },
  'openedx-ai-extensions.settings-modal.workflows.profile.usage-scopes': {
    id: 'openedx-ai-extensions.settings-modal.workflows.profile.usage-scopes',
    defaultMessage: '{count, plural, one {1 scope} other {{count} scopes}}',
    description: 'Badge showing how many scopes link to this AI workflow profile',
  },
});

export default messages;
