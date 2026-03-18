export type FlashcardStep = 'idle' | 'generating' | 'loading' | 'studying' | 'saving' | 'error';

export interface Flashcard {
  id: string;
  question: string;
  answer: string;
  nextReviewTime: number;
  interval: number;
  easeFactor: number;
  repetitions: number;
  lastReviewedAt: number | null;
}

export interface CardStack {
  cards: Flashcard[];
  createdAt: number;
  lastStudiedAt: number | null;
}

export interface IntervalChoice {
  relativeTime: { value: number; unit: 'second' | 'minute' | 'hour' | 'day' | 'week' };
  minutes: number;
  quality: number;
}
