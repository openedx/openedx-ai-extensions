import { defineMessages } from '@edx/frontend-platform/i18n';

const messages = defineMessages({
  'ai.library.creator.title': {
    id: 'ai.library.creator.title',
    defaultMessage: 'AI Question Creator',
    description: 'Title for the library component creator',
  },
  'ai.library.creator.description': {
    id: 'ai.library.creator.description',
    defaultMessage: 'Generate quiz questions from this unit content and review them before saving to a library.',
    description: 'Description for the library component creator',
  },
  'ai.library.creator.start.button': {
    id: 'ai.library.creator.start.button',
    defaultMessage: 'Generate Questions',
    description: 'Button to open the generation form',
  },
  'ai.library.creator.cancel': {
    id: 'ai.library.creator.cancel',
    defaultMessage: 'Cancel',
    description: 'Cancel button text',
  },
  'ai.library.creator.start.over': {
    id: 'ai.library.creator.start.over',
    defaultMessage: 'Start Over',
    description: 'Reset to idle and clear session',
  },
  'ai.library.creator.questions.label': {
    id: 'ai.library.creator.questions.label',
    defaultMessage: 'Number of Questions',
    description: 'Label for number of questions input',
  },
  'ai.library.creator.questions.help': {
    id: 'ai.library.creator.questions.help',
    defaultMessage: 'How many questions to generate (1–20)',
    description: 'Help text for number of questions',
  },
  'ai.library.creator.questions.error': {
    id: 'ai.library.creator.questions.error',
    defaultMessage: 'Number of questions must be between 1 and 20.',
    description: 'Validation error for number of questions',
  },
  'ai.library.creator.instructions.label': {
    id: 'ai.library.creator.instructions.label',
    defaultMessage: 'Additional Instructions (Optional)',
    description: 'Label for additional instructions textarea',
  },
  'ai.library.creator.instructions.placeholder': {
    id: 'ai.library.creator.instructions.placeholder',
    defaultMessage: 'e.g. Focus on key concepts, use plain language…',
    description: 'Placeholder for additional instructions',
  },
  'ai.library.creator.generate.button': {
    id: 'ai.library.creator.generate.button',
    defaultMessage: 'Generate',
    description: 'Submit button for the generation form',
  },
  'ai.library.creator.generating': {
    id: 'ai.library.creator.generating',
    defaultMessage: 'Generating questions…',
    description: 'Status message while generating',
  },
  'ai.library.creator.review.heading': {
    id: 'ai.library.creator.review.heading',
    defaultMessage: '{count, plural, one {# question generated} other {# questions generated}} — review before saving',
    description: 'Review step heading with question count',
  },
  'ai.library.creator.collection.name.label': {
    id: 'ai.library.creator.collection.name.label',
    defaultMessage: 'Collection Name',
    description: 'Label for the collection name input in the save step',
  },
  'ai.library.creator.collection.name.placeholder': {
    id: 'ai.library.creator.collection.name.placeholder',
    defaultMessage: 'e.g. Week 3 Quiz Questions',
    description: 'Placeholder for the collection name input',
  },
  'ai.library.creator.library.label': {
    id: 'ai.library.creator.library.label',
    defaultMessage: 'Target Library',
    description: 'Label for library selection dropdown',
  },
  'ai.library.creator.library.placeholder': {
    id: 'ai.library.creator.library.placeholder',
    defaultMessage: 'Select a library…',
    description: 'Placeholder for library dropdown',
  },
  'ai.library.creator.library.loading': {
    id: 'ai.library.creator.library.loading',
    defaultMessage: 'Loading libraries…',
    description: 'Loading state for library dropdown',
  },
  'ai.library.creator.library.none': {
    id: 'ai.library.creator.library.none',
    defaultMessage: 'No libraries available',
    description: 'No libraries found',
  },
  'ai.library.creator.library.error': {
    id: 'ai.library.creator.library.error',
    defaultMessage: 'Failed to load libraries.',
    description: 'Error loading libraries',
  },
  'ai.library.creator.save.button': {
    id: 'ai.library.creator.save.button',
    defaultMessage: 'Save to Library',
    description: 'Save button to commit questions to library',
  },
  'ai.library.creator.saving': {
    id: 'ai.library.creator.saving',
    defaultMessage: 'Saving to library…',
    description: 'Status message while saving',
  },
  'ai.library.creator.error.generate': {
    id: 'ai.library.creator.error.generate',
    defaultMessage: 'Failed to generate questions. Please try again.',
    description: 'Generic generation error',
  },
  'ai.library.creator.error.save': {
    id: 'ai.library.creator.error.save',
    defaultMessage: 'Failed to save questions. Please try again.',
    description: 'Generic save error',
  },
  'ai.library.creator.error.no.library': {
    id: 'ai.library.creator.error.no.library',
    defaultMessage: 'Please select a library before saving.',
    description: 'Validation error when no library selected',
  },
  'ai.library.creator.error.no.questions': {
    id: 'ai.library.creator.error.no.questions',
    defaultMessage: 'No questions to save. Restore or regenerate at least one question.',
    description: 'Validation error when all questions discarded',
  },
  'ai.library.creator.task.timeout': {
    id: 'ai.library.creator.task.timeout',
    defaultMessage: 'Generation is taking longer than expected. Please try again.',
    description: 'Timeout message during generation polling',
  },
  // Question card messages — field labels
  'ai.library.creator.card.field.question': {
    id: 'ai.library.creator.card.field.question',
    defaultMessage: 'Question',
    description: 'Label for the question text field in the card',
  },
  'ai.library.creator.card.field.choices': {
    id: 'ai.library.creator.card.field.choices',
    defaultMessage: 'Answer Choices',
    description: 'Label for the choices list in the card',
  },
  'ai.library.creator.card.field.answer': {
    id: 'ai.library.creator.card.field.answer',
    defaultMessage: 'Answer',
    description: 'Label for the answer value field in the card',
  },
  'ai.library.creator.card.field.tolerance': {
    id: 'ai.library.creator.card.field.tolerance',
    defaultMessage: 'Tolerance',
    description: 'Label for the numeric tolerance field in the card',
  },
  'ai.library.creator.card.field.explanation': {
    id: 'ai.library.creator.card.field.explanation',
    defaultMessage: 'Explanation',
    description: 'Label for the solution/explanation field in the card',
  },
  'ai.library.creator.card.field.hints': {
    id: 'ai.library.creator.card.field.hints',
    defaultMessage: 'Hints',
    description: 'Label for the demand hints list in the card',
  },
  'ai.library.creator.card.edit': {
    id: 'ai.library.creator.card.edit',
    defaultMessage: 'Edit',
    description: 'Edit question button',
  },
  'ai.library.creator.card.regenerate': {
    id: 'ai.library.creator.card.regenerate',
    defaultMessage: 'Regenerate',
    description: 'Regenerate question button',
  },
  'ai.library.creator.card.discard': {
    id: 'ai.library.creator.card.discard',
    defaultMessage: 'Discard',
    description: 'Discard question button',
  },
  'ai.library.creator.card.restore': {
    id: 'ai.library.creator.card.restore',
    defaultMessage: 'Restore',
    description: 'Restore discarded question button',
  },
  'ai.library.creator.card.discarded.label': {
    id: 'ai.library.creator.card.discarded.label',
    defaultMessage: 'Discarded',
    description: 'Label on discarded question overlay',
  },
  'ai.library.creator.card.regenerating': {
    id: 'ai.library.creator.card.regenerating',
    defaultMessage: 'Regenerating…',
    description: 'Status while regenerating a question',
  },
  'ai.library.creator.card.regenerate.instructions.label': {
    id: 'ai.library.creator.card.regenerate.instructions.label',
    defaultMessage: 'Refinement instructions (optional)',
    description: 'Label for extra instructions field in regenerate form',
  },
  'ai.library.creator.card.regenerate.instructions.placeholder': {
    id: 'ai.library.creator.card.regenerate.instructions.placeholder',
    defaultMessage: 'e.g. Make it harder, use simpler language…',
    description: 'Placeholder for regenerate instructions field',
  },
  'ai.library.creator.card.regenerate.confirm': {
    id: 'ai.library.creator.card.regenerate.confirm',
    defaultMessage: 'Regenerate',
    description: 'Confirm button in the regenerate inline form',
  },
  'ai.library.creator.card.version.counter': {
    id: 'ai.library.creator.card.version.counter',
    defaultMessage: 'Version {current} of {total}',
    description: 'Version counter in the history navigator',
  },
  'ai.library.creator.card.version.previous': {
    id: 'ai.library.creator.card.version.previous',
    defaultMessage: 'Previous version',
    description: 'Previous version button aria-label',
  },
  'ai.library.creator.card.version.next': {
    id: 'ai.library.creator.card.version.next',
    defaultMessage: 'Next version',
    description: 'Next version button aria-label',
  },
  'ai.library.creator.card.correct': {
    id: 'ai.library.creator.card.correct',
    defaultMessage: '✓ Correct',
    description: 'Correct answer marker',
  },
  // Question editor messages
  'ai.library.creator.editor.tab.olx': {
    id: 'ai.library.creator.editor.tab.olx',
    defaultMessage: 'OLX Editor',
    description: 'Tab label for the OLX code editor',
  },
  'ai.library.creator.editor.tab.json': {
    id: 'ai.library.creator.editor.tab.json',
    defaultMessage: 'JSON Editor',
    description: 'Tab label for the JSON field editor',
  },
  'ai.library.creator.editor.tab.olx.hint': {
    id: 'ai.library.creator.editor.tab.olx.hint',
    defaultMessage: 'Edit the raw OLX. Applying will parse the OLX back into the question fields.',
    description: 'Hint text for the OLX editor tab',
  },
  'ai.library.creator.editor.tab.json.hint': {
    id: 'ai.library.creator.editor.tab.json.hint',
    defaultMessage: 'Edit the question data as JSON. The "olx" field is derived automatically.',
    description: 'Hint text for the JSON editor tab',
  },
  'ai.library.creator.editor.json.error': {
    id: 'ai.library.creator.editor.json.error',
    defaultMessage: 'Invalid JSON. Please check the format and try again.',
    description: 'Error shown when JSON editor content cannot be parsed',
  },
  'ai.library.creator.editor.apply': {
    id: 'ai.library.creator.editor.apply',
    defaultMessage: 'Apply',
    description: 'Apply button in the editor to save changes',
  },
  'ai.library.creator.editor.cancel': {
    id: 'ai.library.creator.editor.cancel',
    defaultMessage: 'Cancel',
    description: 'Cancel button in inline editor',
  },
  // Response component messages
  'ai.library.creator.response.title': {
    id: 'ai.library.creator.response.title',
    defaultMessage: 'AI Question Creator',
    description: 'Title for the response component',
  },
  'ai.library.creator.response.message': {
    id: 'ai.library.creator.response.message',
    defaultMessage: 'Questions saved to your Content Library.',
    description: 'Success message in response component',
  },
  'ai.library.creator.response.hyperlink': {
    id: 'ai.library.creator.response.hyperlink',
    defaultMessage: 'View collection >',
    description: 'Hyperlink text for collection URL',
  },
  'ai.library.creator.response.success.detail': {
    id: 'ai.library.creator.response.success.detail',
    defaultMessage: 'The questions have been added to your Content Library in an unpublished state for review.',
    description: 'Detailed success message',
  },
  'ai.library.creator.response.clear': {
    id: 'ai.library.creator.response.clear',
    defaultMessage: 'Start Over',
    description: 'Clear/reset button in response component',
  },
});

export default messages;
