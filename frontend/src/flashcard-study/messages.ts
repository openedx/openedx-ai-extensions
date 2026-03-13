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
  'ai.extensions.flashcard.creator.description': {
    id: 'ai.extensions.flashcard.creator.description',
    defaultMessage: 'Generate flashcards from the course content to study with spaced repetition.',
    description: 'Description shown below the title in the flashcard creator card',
  },
  'ai.extensions.flashcard.creator.create.button': {
    id: 'ai.extensions.flashcard.creator.create.button',
    defaultMessage: 'Create New Cards',
    description: 'Button to open the generate form',
  },
  'ai.extensions.flashcard.creator.display.button': {
    id: 'ai.extensions.flashcard.creator.display.button',
    defaultMessage: 'Display Cards',
    description: 'Button to load and display the existing card stack from session',
  },
  'ai.extensions.flashcard.creator.start.over': {
    id: 'ai.extensions.flashcard.creator.start.over',
    defaultMessage: 'Start Over',
    description: 'Button to return to the idle state after an error',
  },
  'ai.extensions.flashcard.error.network': {
    id: 'ai.extensions.flashcard.error.network',
    defaultMessage: 'A network error occurred. Please check your connection and try again.',
    description: 'Error shown when a network error occurs during generation',
  },
  'ai.extensions.flashcard.error.load': {
    id: 'ai.extensions.flashcard.error.load',
    defaultMessage: 'Failed to load your flashcards. Please try again.',
    description: 'Error shown when loading the session card stack fails',
  },
  'ai.extensions.flashcard.study.progress': {
    id: 'ai.extensions.flashcard.study.progress',
    defaultMessage: 'Card {current} of {total}',
    description: 'Progress indicator showing which card is being studied',
  },
  'ai.extensions.flashcard.study.reviewed': {
    id: 'ai.extensions.flashcard.study.reviewed',
    defaultMessage: '{count} reviewed',
    description: 'Count of cards reviewed in the current session',
  },
  'ai.extensions.flashcard.study.no.cards.due': {
    id: 'ai.extensions.flashcard.study.no.cards.due',
    defaultMessage: 'No cards are due for review right now.',
    description: 'Message shown when all cards have been reviewed and none are due yet',
  },
  'ai.extensions.flashcard.study.next.due': {
    id: 'ai.extensions.flashcard.study.next.due',
    defaultMessage: 'Next card due {time}',
    description: 'Shows when the next card will be due for review',
  },
  'ai.extensions.flashcard.study.save.progress': {
    id: 'ai.extensions.flashcard.study.save.progress',
    defaultMessage: 'Save Progress',
    description: 'Button to save the current study progress to the session',
  },
  'ai.extensions.flashcard.study.saving': {
    id: 'ai.extensions.flashcard.study.saving',
    defaultMessage: 'Saving',
    description: 'Button label while saving is in progress',
  },
  'ai.extensions.flashcard.study.back': {
    id: 'ai.extensions.flashcard.study.back',
    defaultMessage: 'Back',
    description: 'Button to go back to the request component',
  },
  'ai.extensions.flashcard.study.empty': {
    id: 'ai.extensions.flashcard.study.empty',
    defaultMessage: 'No flashcards found. Generate some cards first.',
    description: 'Message shown when the response contains no cards',
  },
  'ai.extensions.flashcard.error.save': {
    id: 'ai.extensions.flashcard.error.save',
    defaultMessage: 'Failed to save progress. Please try again.',
    description: 'Error shown when saving the card stack fails',
  },
});

export default messages;
