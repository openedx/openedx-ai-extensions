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
  'ai.extensions.flashcard.generate.form.auto.help': {
    id: 'ai.extensions.flashcard.generate.form.auto.help',
    defaultMessage: 'Choose a study depth or let AI decide.',
    description: 'Helper text for the depth selector',
  },
  'ai.extensions.flashcard.generate.depth.auto': {
    id: 'ai.extensions.flashcard.generate.depth.auto',
    defaultMessage: 'Auto',
    description: 'Label for the auto depth option',
  },
  'ai.extensions.flashcard.generate.depth.auto.sublabel': {
    id: 'ai.extensions.flashcard.generate.depth.auto.sublabel',
    defaultMessage: 'Optimal',
    description: 'Sublabel for the auto depth option',
  },
  'ai.extensions.flashcard.generate.depth.cards': {
    id: 'ai.extensions.flashcard.generate.depth.cards',
    defaultMessage: '{count} cards',
    description: 'Top label for a numeric depth option showing the card count',
  },
  'ai.extensions.flashcard.generate.depth.quick': {
    id: 'ai.extensions.flashcard.generate.depth.quick',
    defaultMessage: 'Quick',
    description: 'Sublabel for the quick depth option',
  },
  'ai.extensions.flashcard.generate.depth.standard': {
    id: 'ai.extensions.flashcard.generate.depth.standard',
    defaultMessage: 'Standard',
    description: 'Sublabel for the standard depth option',
  },
  'ai.extensions.flashcard.generate.depth.deep': {
    id: 'ai.extensions.flashcard.generate.depth.deep',
    defaultMessage: 'Deep',
    description: 'Sublabel for the deep depth option',
  },
  'ai.extensions.flashcard.generating': {
    id: 'ai.extensions.flashcard.generating',
    defaultMessage: 'Generating',
    description: 'Submit button label while generation is in progress',
  },
  'ai.extensions.flashcard.creator.loading': {
    id: 'ai.extensions.flashcard.creator.loading',
    defaultMessage: 'Loading',
    description: 'Generic spinner text while loading',
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
    defaultMessage: "Let's Practice",
    description: 'Button to open the modal and study the existing card deck',
  },
  'ai.extensions.flashcard.creator.display.button.due': {
    id: 'ai.extensions.flashcard.creator.display.button.due',
    defaultMessage: 'cards due',
    description: 'Screen reader text for the due cards badge on the practice button',
  },
  'ai.extensions.flashcard.error.network': {
    id: 'ai.extensions.flashcard.error.network',
    defaultMessage: 'A network error occurred. Please check your connection and try again.',
    description: 'Error shown when a network error occurs during generation',
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
    defaultMessage: "You're all caught up!",
    description: 'Title shown when all cards have been reviewed and none are due yet',
  },
  'ai.extensions.flashcard.study.no.cards.due.description': {
    id: 'ai.extensions.flashcard.study.no.cards.due.description',
    defaultMessage: 'Your memory of this unit is fresh. Your next scheduled review will appear here when it\'s time.',
    description: 'Description shown when all cards have been reviewed and none are due yet',
  },
  'ai.extensions.flashcard.study.done': {
    id: 'ai.extensions.flashcard.study.done',
    defaultMessage: 'Done',
    description: 'Button to close the study modal and return to the request component',
  },
  'ai.extensions.flashcard.error.save': {
    id: 'ai.extensions.flashcard.error.save',
    defaultMessage: 'Failed to save progress.',
    description: 'Error shown when saving the card stack fails',
  },
  'ai.extensions.flashcard.error.save.retry': {
    id: 'ai.extensions.flashcard.error.save.retry',
    defaultMessage: 'Retry',
    description: 'Button to retry saving the card stack after a failure',
  },
  'ai.extensions.flashcard.study.session.description': {
    id: 'ai.extensions.flashcard.study.session.description',
    defaultMessage: 'Use your flashcards to review the course content.',
    description: 'Message shown when a preloaded session has cards available',
  },
  'ai.extensions.flashcard.study.paused.session.justNow': {
    id: 'ai.extensions.flashcard.study.paused.session.justNow',
    defaultMessage: 'Last review: just now',
    description: 'Text shown when the last review was less than a minute ago',
  },
  'ai.extensions.flashcard.study.paused.session.lastReview': {
    id: 'ai.extensions.flashcard.study.paused.session.lastReview',
    defaultMessage: 'Last review: {time}',
    description: 'Small text showing when the last card review happened',
  },
  'ai.extensions.flashcard.study.clear.session': {
    id: 'ai.extensions.flashcard.study.clear.session',
    defaultMessage: 'Generate Unit Cards',
    description: 'Generate cards for the current unit and add it to the course deck',
  },
});

export default messages;
