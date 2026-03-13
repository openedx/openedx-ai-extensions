import { renderHook, act } from '@testing-library/react';
import { Flashcard } from '../types';
import { useStudySession } from './useStudySession';

const makeCard = (id: string, nextReviewTime: number): Flashcard => ({
  id,
  question: `Q${id}`,
  answer: `A${id}`,
  nextReviewTime,
  interval: 1,
  easeFactor: 2.5,
  repetitions: 0,
  lastReviewedAt: null,
});

describe('useStudySession', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.spyOn(Date, 'now').mockReturnValue(1_000_000);
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it('filters due cards based on nextReviewTime <= now', () => {
    const cards = [
      makeCard('1', 500_000),   // due (past)
      makeCard('2', 2_000_000), // not due (future)
      makeCard('3', 1_000_000), // due (exactly now)
    ];

    const { result } = renderHook(() => useStudySession({ cards }));

    expect(result.current.dueCards).toHaveLength(2);
    expect(result.current.dueCards.map((c) => c.id)).toEqual(['1', '3']);
  });

  it('returns the first due card as currentCard', () => {
    const cards = [makeCard('1', 500_000), makeCard('2', 600_000)];

    const { result } = renderHook(() => useStudySession({ cards }));

    expect(result.current.currentCard?.id).toBe('1');
  });

  it('returns null currentCard when no cards are due', () => {
    const cards = [makeCard('1', 2_000_000)];

    const { result } = renderHook(() => useStudySession({ cards }));

    expect(result.current.currentCard).toBeNull();
  });

  it('advances to the next due card on nextCard()', () => {
    const cards = [makeCard('1', 500_000), makeCard('2', 600_000)];

    const { result } = renderHook(() => useStudySession({ cards }));

    act(() => {
      result.current.nextCard();
    });

    expect(result.current.currentCard?.id).toBe('2');
  });

  it('wraps around to the first card when reaching the end', () => {
    const cards = [makeCard('1', 500_000)];

    const { result } = renderHook(() => useStudySession({ cards }));

    act(() => {
      result.current.nextCard();
    });

    // Only 1 due card, so index wraps to 0
    expect(result.current.currentCard?.id).toBe('1');
  });

  it('returns nextDueIn as 0 when there are due cards', () => {
    const cards = [makeCard('1', 500_000)];

    const { result } = renderHook(() => useStudySession({ cards }));

    expect(result.current.nextDueIn).toBe(0);
  });

  it('returns nextDueIn as ms until next card when none are due', () => {
    const cards = [makeCard('1', 1_060_000)]; // 60s from now

    const { result } = renderHook(() => useStudySession({ cards }));

    expect(result.current.nextDueIn).toBe(60_000);
  });

  it('returns nextDueIn as null when the stack is empty', () => {
    const { result } = renderHook(() => useStudySession({ cards: [] }));

    expect(result.current.nextDueIn).toBeNull();
  });

  it('resetSession resets to the first card', () => {
    const cards = [makeCard('1', 500_000), makeCard('2', 600_000)];

    const { result } = renderHook(() => useStudySession({ cards }));

    act(() => { result.current.nextCard(); });

    expect(result.current.currentCard?.id).toBe('2');

    act(() => { result.current.resetSession(); });

    expect(result.current.currentCard?.id).toBe('1');
  });

  it('derives reviewedCount from cards with lastReviewedAt set', () => {
    const cards = [
      { ...makeCard('1', 500_000), lastReviewedAt: 999_000 },
      makeCard('2', 600_000),
    ];

    const { result } = renderHook(() => useStudySession({ cards }));

    expect(result.current.reviewedCount).toBe(1);
  });

  it('returns reviewedCount 0 when no cards have been rated yet', () => {
    const cards = [makeCard('1', 500_000), makeCard('2', 600_000)];

    const { result } = renderHook(() => useStudySession({ cards }));

    expect(result.current.reviewedCount).toBe(0);
  });

  it('cleans up interval on unmount', () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
    const cards = [makeCard('1', 500_000)];

    const { unmount } = renderHook(() => useStudySession({ cards }));

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
