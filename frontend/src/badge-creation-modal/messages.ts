import { defineMessages } from '@edx/frontend-platform/i18n';

const messages = defineMessages({
  // Modal titles and headers
  modalTitle: {
    id: 'openedx-ai-extensions.badge-creation-modal.title',
    defaultMessage: 'AI Badge Creator',
    description: 'Title of the badge creation modal',
  },

  // Step 1: Badge Form
  formStepTitle: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.title',
    defaultMessage: 'Create Your Badge',
    description: 'Title for the badge form step',
  },

  // Scope selection
  scopeLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.scope.label',
    defaultMessage: 'Badge Scope',
    description: 'Label for badge scope selection',
  },

  scopeDescription: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.scope.description',
    defaultMessage: 'Choose which part of the course this badge applies to',
    description: 'Description for scope selection',
  },

  scopeCourse: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.scope.course',
    defaultMessage: 'Course',
    description: 'Scope option for entire course',
  },

  scopeSection: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.scope.section',
    defaultMessage: 'Section',
    description: 'Scope option for section',
  },

  scopeUnit: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.scope.unit',
    defaultMessage: 'Unit',
    description: 'Scope option for specific unit',
  },

  // Unit selection
  unitLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.unit.label',
    defaultMessage: 'Select Unit',
    description: 'Label for unit selection dropdown',
  },

  unitPlaceholder: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.unit.placeholder',
    defaultMessage: 'Choose a unit',
    description: 'Placeholder for unit selection',
  },

  // Badge style selection
  styleLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.style.label',
    defaultMessage: 'Badge Style',
    description: 'Label for badge style selection',
  },

  styleModern: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.style.modern',
    defaultMessage: 'Modern',
    description: 'Modern badge style option',
  },

  styleClassic: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.style.classic',
    defaultMessage: 'Classic',
    description: 'Classic badge style option',
  },

  styleMinimalist: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.style.minimalist',
    defaultMessage: 'Minimalist',
    description: 'Minimalist badge style option',
  },

  stylePlayful: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.style.playful',
    defaultMessage: 'Playful',
    description: 'Playful badge style option',
  },

  // Badge tone selection
  toneLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.tone.label',
    defaultMessage: 'Badge Tone',
    description: 'Label for badge tone selection',
  },

  // Additional description field
  descriptionLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.description.label',
    defaultMessage: 'Additional Description',
    description: 'Label for additional badge description field',
  },

  descriptionPlaceholder: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.description.placeholder',
    defaultMessage: 'Provide any additional context or details about this badge',
    description: 'Placeholder text for description textarea',
  },

  toneProfessional: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.tone.professional',
    defaultMessage: 'Professional',
    description: 'Professional badge tone option',
  },

  toneFriendly: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.tone.friendly',
    defaultMessage: 'Friendly',
    description: 'Friendly badge tone option',
  },

  toneAcademic: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.tone.academic',
    defaultMessage: 'Academic',
    description: 'Academic badge tone option',
  },

  toneCreative: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.tone.creative',
    defaultMessage: 'Creative',
    description: 'Creative badge tone option',
  },

  // Badge level selection
  levelLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.level.label',
    defaultMessage: 'Badge Level',
    description: 'Label for badge level selection',
  },

  levelBeginner: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.level.beginner',
    defaultMessage: 'Beginner',
    description: 'Beginner badge level option',
  },

  levelIntermediate: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.level.intermediate',
    defaultMessage: 'Intermediate',
    description: 'Intermediate badge level option',
  },

  levelAdvanced: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.level.advanced',
    defaultMessage: 'Advanced',
    description: 'Advanced badge level option',
  },

  levelExpert: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.level.expert',
    defaultMessage: 'Expert',
    description: 'Expert badge level option',
  },

  // Badge criterion selection
  criterionLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.criterion.label',
    defaultMessage: 'Badge Criterion',
    description: 'Label for badge criterion selection',
  },

  criterionCompletion: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.criterion.completion',
    defaultMessage: 'Completion',
    description: 'Completion criterion option',
  },

  criterionMastery: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.criterion.mastery',
    defaultMessage: 'Mastery',
    description: 'Mastery criterion option',
  },

  criterionParticipation: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.criterion.participation',
    defaultMessage: 'Participation',
    description: 'Participation criterion option',
  },

  criterionExcellence: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.criterion.excellence',
    defaultMessage: 'Excellence',
    description: 'Excellence criterion option',
  },

  // Skills toggle
  skillsEnabledLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.skills.label',
    defaultMessage: 'Extract Skills',
    description: 'Label for skill extraction toggle',
  },

  skillsEnabledDescription: {
    id: 'openedx-ai-extensions.badge-creation-modal.form.skills.description',
    defaultMessage: 'Automatically extract and align skills from the selected {scope}',
    description: 'Description for skill extraction feature',
  },

  // Buttons
  generateButton: {
    id: 'openedx-ai-extensions.badge-creation-modal.button.generate',
    defaultMessage: 'Generate Badge',
    description: 'Button to generate badge',
  },

  saveButton: {
    id: 'openedx-ai-extensions.badge-creation-modal.button.save',
    defaultMessage: 'Save Badge',
    description: 'Button to save badge',
  },

  refinButton: {
    id: 'openedx-ai-extensions.badge-creation-modal.button.refine',
    defaultMessage: 'Refine Badge',
    description: 'Button to refine badge',
  },

  newBadgeButton: {
    id: 'openedx-ai-extensions.badge-creation-modal.button.new',
    defaultMessage: 'Create New Badge',
    description: 'Button to start creating new badge',
  },

  closeButton: {
    id: 'openedx-ai-extensions.badge-creation-modal.button.close',
    defaultMessage: 'Close',
    description: 'Button to close modal',
  },

  backButton: {
    id: 'openedx-ai-extensions.badge-creation-modal.button.back',
    defaultMessage: 'Back',
    description: 'Button to go back',
  },

  cancelButton: {
    id: 'openedx-ai-extensions.badge-creation-modal.button.cancel',
    defaultMessage: 'Cancel',
    description: 'Button to cancel action',
  },

  // Step 2: Generation
  generatingTitle: {
    id: 'openedx-ai-extensions.badge-creation-modal.generating.title',
    defaultMessage: 'Generating Your Badge',
    description: 'Title shown during generation',
  },

  generatingMessage: {
    id: 'openedx-ai-extensions.badge-creation-modal.generating.message',
    defaultMessage: 'Please wait while AI creates your badge',
    description: 'Message shown during generation',
  },

  // Step 3: Preview
  previewTitle: {
    id: 'openedx-ai-extensions.badge-creation-modal.preview.title',
    defaultMessage: 'Your Generated Badge',
    description: 'Title for badge preview',
  },

  previewDescription: {
    id: 'openedx-ai-extensions.badge-creation-modal.preview.description',
    defaultMessage: 'Review your badge below. You can provide feedback to refine it.',
    description: 'Description for preview step',
  },

  // Step 4: Feedback
  feedbackTitle: {
    id: 'openedx-ai-extensions.badge-creation-modal.feedback.title',
    defaultMessage: 'Refine Your Badge',
    description: 'Title for feedback step',
  },

  feedbackPromptLabel: {
    id: 'openedx-ai-extensions.badge-creation-modal.feedback.prompt.label',
    defaultMessage: 'What would you like to change?',
    description: 'Label for feedback input',
  },

  feedbackPromptPlaceholder: {
    id: 'openedx-ai-extensions.badge-creation-modal.feedback.prompt.placeholder',
    defaultMessage: 'e.g., "Make the colors more professional" or "Add mathematical symbols"',
    description: 'Placeholder for feedback input',
  },

  iterationCount: {
    id: 'openedx-ai-extensions.badge-creation-modal.feedback.iteration.count',
    defaultMessage: 'Iteration {count}',
    description: 'Shows current iteration count',
  },

  // Step 5: Save
  savingTitle: {
    id: 'openedx-ai-extensions.badge-creation-modal.saving.title',
    defaultMessage: 'Saving Your Badge',
    description: 'Title shown while saving',
  },

  savingMessage: {
    id: 'openedx-ai-extensions.badge-creation-modal.saving.message',
    defaultMessage: 'Please wait while your badge is being saved...',
    description: 'Message shown while saving',
  },

  // Success/Completion
  completionTitle: {
    id: 'openedx-ai-extensions.badge-creation-modal.completion.title',
    defaultMessage: 'Badge Created Successfully!',
    description: 'Success message title',
  },

  completionMessage: {
    id: 'openedx-ai-extensions.badge-creation-modal.completion.message',
    defaultMessage: 'Your badge has been saved to the course files.',
    description: 'Success message description',
  },

  // Error messages
  requiredFieldError: {
    id: 'openedx-ai-extensions.badge-creation-modal.error.required-field',
    defaultMessage: 'This field is required',
    description: 'Error for required field',
  },

  generationError: {
    id: 'openedx-ai-extensions.badge-creation-modal.error.generation',
    defaultMessage: 'Failed to generate badge. Please try again.',
    description: 'Error message for generation failure',
  },

  savingError: {
    id: 'openedx-ai-extensions.badge-creation-modal.error.saving',
    defaultMessage: 'Failed to save badge. Please try again.',
    description: 'Error message for save failure',
  },

  networkError: {
    id: 'openedx-ai-extensions.badge-creation-modal.error.network',
    defaultMessage: 'Network error. Please check your connection and try again.',
    description: 'Error message for network issues',
  },
  'openedx-ai-extensions.badge-creation-card.title': {
    id: 'openedx-ai-extensions.badge-creation-card.title',
    defaultMessage: 'Create AI Badge',
    description: 'Title of the badge creation card',
  },
  'openedx-ai-extensions.badge-creation-card.description': {
    id: 'openedx-ai-extensions.badge-creation-card.description',
    defaultMessage: 'Create custom badges for your course using AI.',
    description: 'Description of the badge creation card',
  },
  'openedx-ai-extensions.badge-creation-card.new': {
    id: 'openedx-ai-extensions.badge-creation-card.new',
    defaultMessage: 'New',
    description: 'Label for new feature',
  },
});

export default messages;
