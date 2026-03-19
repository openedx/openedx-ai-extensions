import {
  useState, useCallback, useEffect, useRef, useReducer,
} from 'react';
import { Flashcard } from '../types';

const DUE_CHECK_INTERVAL = 30_000;

interface UseStudySessionOptions {
  cards: Flashcard[];
}

/**
 * Manages the study session lifecycle for a set of flashcards.
 *
 * Filters cards whose `nextReviewTime` has passed (due cards), cycles through
 * them as the learner reviews, and periodically re-checks for newly due cards
 * every 30 seconds.
 *
 * @param options.cards - The full set of flashcards in the current stack.
 * @returns currentCard  - The card currently being studied, or `null` if none are due.
 * @returns dueCards      - All cards whose review time has arrived.
 * @returns nextCard      - Advances to the next due card after rating and increments reviewedCount.
 * @returns reviewedCount - How many cards were reviewed in the current cycle.
 *                          Resets when new cards become due after being caught up.
 * @returns resetSession  - Resets the index and reviewed count to start over.
 */
export const useStudySession = ({ cards }: UseStudySessionOptions) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [reviewedCount, setReviewedCount] = useState(0);
  const [, forceUpdate] = useReducer((x: number) => x + 1, 0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevDueCountRef = useRef(0);

  // Computed on every render — recomputed when forceUpdate triggers a re-render
  const dueCards = cards.filter((c) => c.nextReviewTime <= Date.now());

  const safeIndex = dueCards.length > 0 ? currentIndex % dueCards.length : 0;
  const currentCard = dueCards[safeIndex] ?? null;

  // Reset reviewed count when new cards become due
  useEffect(() => {
    if (dueCards.length > prevDueCountRef.current) {
      setReviewedCount(0);
    }
    prevDueCountRef.current = dueCards.length;
  }, [dueCards.length]);

  const nextCard = useCallback(() => {
    setReviewedCount((prev) => prev + 1);
    forceUpdate();
    setCurrentIndex((prev) => {
      const next = prev + 1;
      return next < dueCards.length ? next : 0;
    });
  }, [dueCards.length]);

  const resetSession = useCallback(() => {
    setCurrentIndex(0);
    setReviewedCount(0);
    forceUpdate();
  }, []);

  // Periodically re-check which cards are due
  useEffect(() => {
    intervalRef.current = setInterval(forceUpdate, DUE_CHECK_INTERVAL);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    currentCard,
    dueCards,
    nextCard,
    reviewedCount,
    resetSession,
  };
};
