import { defineMessages } from '@edx/frontend-platform/i18n';

const messages = defineMessages({
  'ai.extensions.flashcard.title': {
    id: 'ai.extensions.flashcard.title',
    defaultMessage: 'AI Flashcard Study',
    description: 'Title for the flashcard study feature',
  },
  'ai.extensions.flashcard.error.generate': {
    id: 'ai.extensions.flashcard.error.generate',
    defaultMessage: 'Failed to generate flashcards. Please try again.',
    description: 'Generic generation error',
  },
  'ai.extensions.flashcard.error.timeout': {
    id: 'ai.extensions.flashcard.error.timeout',
    defaultMessage: 'Generation timed out. Please try again.',
    description: 'Error shown when the generation task polling exceeds the maximum duration',
  },
  'ai.extensions.flashcard.card.question.label': {
    id: 'ai.extensions.flashcard.card.question.label',
    defaultMessage: 'Question',
    description: 'Label shown on the question face of the flashcard',
  },
  'ai.extensions.flashcard.card.answer.label': {
    id: 'ai.extensions.flashcard.card.answer.label',
    defaultMessage: 'Answer',
    description: 'Label shown on the answer face of the flashcard',
  },
  'ai.extensions.flashcard.card.show.answer': {
    id: 'ai.extensions.flashcard.card.show.answer',
    defaultMessage: 'Show Answer',
    description: 'Button label to flip the flashcard to the answer side',
  },
  'ai.extensions.flashcard.card.show.question': {
    id: 'ai.extensions.flashcard.card.show.question',
    defaultMessage: 'Show Question',
    description: 'Button label to flip the flashcard back to the question side',
  },
  'ai.extensions.flashcard.controls.again': {
    id: 'ai.extensions.flashcard.controls.again',
    defaultMessage: 'Again',
    description: 'Rating label for "Again" (fail)',
  },
  'ai.extensions.flashcard.controls.hard': {
    id: 'ai.extensions.flashcard.controls.hard',
    defaultMessage: 'Hard',
    description: 'Rating label for "Hard"',
  },
  'ai.extensions.flashcard.controls.good': {
    id: 'ai.extensions.flashcard.controls.good',
    defaultMessage: 'Good',
    description: 'Rating label for "Good"',
  },
  'ai.extensions.flashcard.controls.easy': {
    id: 'ai.extensions.flashcard.controls.easy',
    defaultMessage: 'Easy',
    description: 'Rating label for "Easy"',
  },
  'ai.extensions.flashcard.generate.form.label': {
    id: 'ai.extensions.flashcard.generate.form.label',
    defaultMessage: 'Number of flashcards',
    description: 'Label for the number of cards input in the generate form',
  },
  'ai.extensions.flashcard.generate.form.help': {
    id: 'ai.extensions.flashcard.generate.form.help',
    defaultMessage: 'Choose between 1 and 10',
    description: 'Help text for the number of cards input',
  },
  'ai.extensions.flashcard.generate.form.error': {
    id: 'ai.extensions.flashcard.generate.form.error',
    defaultMessage: 'Number of flashcards must be between 1 and 10.',
    description: 'Validation error for the number of cards input',
  },
  'ai.extensions.flashcard.generate.form.submit': {
    id: 'ai.extensions.flashcard.generate.form.submit',
    defaultMessage: 'Generate',
    description: 'Submit button label for the generate form',
  },
  'ai.extensions.flashcard.generate.form.generating': {
    id: 'ai.extensions.flashcard.generate.form.generating',
    defaultMessage: 'Generating',
    description: 'Submit button label while generation is in progress',
  },
});

export default messages;
