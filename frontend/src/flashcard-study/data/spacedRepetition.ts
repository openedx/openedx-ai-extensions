import { Flashcard, IntervalChoice } from '../types';

// SM-2 algorithm floor: below 1.3 intervals shrink too aggressively, causing review fatigue.
const MIN_EASE_FACTOR = 1.3;
// SM-2 starting ease: 2.5 is the original Pimsleur/Wozniak default, producing a balanced
// initial spacing curve (1m → 10m → 25m → 63m …) before adapting to the learner's performance.
const DEFAULT_EASE_FACTOR = 2.5;

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
 * Simplified SM-2 spaced repetition algorithm.
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

  if (quality < 3) {
    newRepetitions = 0;
    newInterval = 1;
  } else {
    newRepetitions = repetitions + 1;
    if (newRepetitions === 1) {
      newInterval = 1;
    } else if (newRepetitions === 2) {
      newInterval = 10;
    } else {
      newInterval = Math.round(currentInterval * easeFactor);
    }
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
}

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
}

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
}

/**
 * Create default SM-2 values for a new flashcard.
 */
export const createDefaultSM2 = (): Pick<Flashcard, 'interval' | 'easeFactor' | 'repetitions' | 'nextReviewTime' | 'lastReviewedAt'> => {
  return {
    interval: 0,
    easeFactor: DEFAULT_EASE_FACTOR,
    repetitions: 0,
    nextReviewTime: Date.now(),
    lastReviewedAt: null,
  };
}
