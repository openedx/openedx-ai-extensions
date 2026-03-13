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
});

export default messages;
