import { Flashcard, IntervalChoice } from './types';

// SM-2 algorithm floor: below 1.3 intervals shrink too aggressively, causing review fatigue.
const MIN_EASE_FACTOR = 1.3;
// SM-2 starting ease: 2.5 is the original Pimsleur/Wozniak default, producing a balanced
// initial spacing curve before adapting to the learner's performance.
const DEFAULT_EASE_FACTOR = 2.5;
// Anki-style multiplier for Hard: shorter than Good but not a full reset.
const HARD_MULTIPLIER = 1.2;
// Anki-style bonus multiplier for Easy: longer than Good to reward confidence.
const EASY_BONUS = 1.3;

// Fixed graduated steps for the first two repetitions (in minutes).
// Each row: [Again, Hard, Good, Easy]
const GRADUATED_STEPS: Record<number, [number, number, number, number]> = {
  0: [1, 3, 5, 10],
  1: [1, 5, 10, 20],
};

export interface SM2Result {
  interval: number;
  easeFactor: number;
  repetitions: number;
  nextReviewTime: number;
}

export interface RelativeTimeValue {
  value: number;
  unit: 'second' | 'minute' | 'hour' | 'day' | 'week';
}

/**
 * SM-2 spaced repetition algorithm with Anki-style interval differentiation.
 *
 * Quality ratings produce distinct intervals:
 * - Again (0–1): resets repetitions, short fixed interval
 * - Hard (2): keeps repetitions, interval × 1.2 (or graduated step)
 * - Good (3–4): increments repetitions, interval × easeFactor (or graduated step)
 * - Easy (5): increments repetitions, interval × easeFactor × 1.3 (or graduated step)
 *
 * @param quality - User rating 0–5 (0 = complete failure, 5 = perfect)
 * @param currentInterval - Current interval in minutes
 * @param easeFactor - Current ease factor (≥ 1.3)
 * @param repetitions - Number of consecutive successful reviews
 */
export const calculateNextReview = (
  quality: number,
  currentInterval: number,
  easeFactor: number,
  repetitions: number,
): SM2Result => {
  let newInterval: number;
  let newRepetitions: number;
  let newEaseFactor = easeFactor;

  const steps = GRADUATED_STEPS[repetitions];

  if (quality <= 1) {
    // Again: full reset
    newRepetitions = 0;
    newInterval = steps ? steps[0] : 1;
  } else if (quality === 2) {
    // Hard: no reset, no increment — use shorter multiplier
    newRepetitions = repetitions;
    newInterval = steps ? steps[1] : Math.round(currentInterval * HARD_MULTIPLIER);
  } else if (quality <= 4) {
    // Good: standard SM-2 progression
    newRepetitions = repetitions + 1;
    newInterval = steps ? steps[2] : Math.round(currentInterval * easeFactor);
  } else {
    // Easy: SM-2 progression with bonus
    newRepetitions = repetitions + 1;
    newInterval = steps ? steps[3] : Math.round(currentInterval * easeFactor * EASY_BONUS);
  }

  // SM-2 ease factor update
  newEaseFactor += 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02);
  newEaseFactor = Math.max(MIN_EASE_FACTOR, newEaseFactor);

  return {
    interval: newInterval,
    easeFactor: newEaseFactor,
    repetitions: newRepetitions,
    nextReviewTime: Date.now() + newInterval * 60_000,
  };
};

/**
 * Convert an interval in minutes to a { value, unit } tuple
 * suitable for intl.formatRelativeTime(value, unit).
 */
export const toRelativeTime = (minutes: number): RelativeTimeValue => {
  if (minutes < 60) {
    return { value: minutes, unit: 'minute' };
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return { value: hours, unit: 'hour' };
  }
  const days = Math.round(hours / 24);
  if (days < 7) {
    return { value: days, unit: 'day' };
  }
  const weeks = Math.round(days / 7);
  return { value: weeks, unit: 'week' };
};

/**
 * Compute the four interval choices for a given card's current state.
 * Returns projected intervals for Again, Hard, Good, Easy.
 * Labels are { value, unit } tuples — format with intl.formatRelativeTime().
 */
export const getIntervalChoices = (card: Flashcard): IntervalChoice[] => {
  const { interval, easeFactor, repetitions } = card;

  const again = calculateNextReview(1, interval, easeFactor, repetitions);
  const hard = calculateNextReview(2, interval, easeFactor, repetitions);
  const good = calculateNextReview(3, interval, easeFactor, repetitions);
  const easy = calculateNextReview(5, interval, easeFactor, repetitions);

  return [
    { relativeTime: toRelativeTime(again.interval), minutes: again.interval, quality: 1 },
    { relativeTime: toRelativeTime(hard.interval), minutes: hard.interval, quality: 2 },
    { relativeTime: toRelativeTime(good.interval), minutes: good.interval, quality: 3 },
    { relativeTime: toRelativeTime(easy.interval), minutes: easy.interval, quality: 5 },
  ];
};

/**
 * Create default SM-2 values for a new flashcard.
 */
export const createDefaultSM2 = (): Pick<Flashcard, 'interval' | 'easeFactor' | 'repetitions' | 'nextReviewTime' | 'lastReviewedAt'> => ({
  interval: 0,
  easeFactor: DEFAULT_EASE_FACTOR,
  repetitions: 0,
  nextReviewTime: Date.now(),
  lastReviewedAt: null,
});
