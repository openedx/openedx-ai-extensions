import {
  calculateNextReview, toRelativeTime, getIntervalChoices, createDefaultSM2,
} from './spacedRepetition';

describe('calculateNextReview', () => {
  beforeEach(() => {
    jest.spyOn(Date, 'now').mockReturnValue(1_000_000);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('resets interval to 1 minute when quality < 3', () => {
    const result = calculateNextReview(2, 100, 2.5, 5);
    expect(result.interval).toBe(1);
    expect(result.repetitions).toBe(0);
  });

  it('sets interval to 1 minute on first successful review', () => {
    const result = calculateNextReview(3, 0, 2.5, 0);
    expect(result.interval).toBe(1);
    expect(result.repetitions).toBe(1);
  });

  it('sets interval to 10 minutes on second successful review', () => {
    const result = calculateNextReview(4, 1, 2.5, 1);
    expect(result.interval).toBe(10);
    expect(result.repetitions).toBe(2);
  });

  it('multiplies interval by ease factor on subsequent reviews', () => {
    const result = calculateNextReview(4, 10, 2.5, 2);
    expect(result.interval).toBe(25);
    expect(result.repetitions).toBe(3);
  });

  it('never lets ease factor drop below 1.3', () => {
    const result = calculateNextReview(0, 10, 1.3, 3);
    expect(result.easeFactor).toBeGreaterThanOrEqual(1.3);
  });

  it('increases ease factor for high quality ratings', () => {
    const result = calculateNextReview(5, 10, 2.5, 2);
    expect(result.easeFactor).toBeGreaterThan(2.5);
  });

  it('computes nextReviewTime from interval', () => {
    const result = calculateNextReview(3, 0, 2.5, 0);
    // interval = 1 minute = 60_000ms, Date.now() = 1_000_000
    expect(result.nextReviewTime).toBe(1_000_000 + 60_000);
  });
});

describe('toRelativeTime', () => {
  it('returns minutes for values under 60', () => {
    expect(toRelativeTime(1)).toEqual({ value: 1, unit: 'minute' });
    expect(toRelativeTime(30)).toEqual({ value: 30, unit: 'minute' });
  });

  it('returns hours for values from 60 to under 1440', () => {
    expect(toRelativeTime(60)).toEqual({ value: 1, unit: 'hour' });
    expect(toRelativeTime(120)).toEqual({ value: 2, unit: 'hour' });
  });

  it('returns days for values from 1440 to under 10080', () => {
    expect(toRelativeTime(1440)).toEqual({ value: 1, unit: 'day' });
    expect(toRelativeTime(4320)).toEqual({ value: 3, unit: 'day' });
  });

  it('returns weeks for values of 10080 and above', () => {
    expect(toRelativeTime(10080)).toEqual({ value: 1, unit: 'week' });
    expect(toRelativeTime(20160)).toEqual({ value: 2, unit: 'week' });
  });
});

describe('getIntervalChoices', () => {
  const card = {
    id: '1',
    question: 'Q',
    answer: 'A',
    nextReviewTime: 0,
    interval: 10,
    easeFactor: 2.5,
    repetitions: 2,
    lastReviewedAt: null,
  };

  it('returns exactly 4 choices', () => {
    const choices = getIntervalChoices(card);
    expect(choices).toHaveLength(4);
  });

  it('assigns correct quality values', () => {
    const choices = getIntervalChoices(card);
    expect(choices.map((c) => c.quality)).toEqual([1, 2, 3, 5]);
  });

  it('Again (quality=1) resets to 1 minute', () => {
    const choices = getIntervalChoices(card);
    expect(choices[0].minutes).toBe(1);
    expect(choices[0].relativeTime).toEqual({ value: 1, unit: 'minute' });
  });

  it('Hard (quality=2) also resets to 1 minute', () => {
    const choices = getIntervalChoices(card);
    expect(choices[1].minutes).toBe(1);
  });

  it('Good (quality=3) uses SM-2 progression', () => {
    const choices = getIntervalChoices(card);
    // repetitions=2 → interval * easeFactor = 10 * 2.5 = 25
    expect(choices[2].minutes).toBe(25);
  });

  it('Easy (quality=5) uses SM-2 progression', () => {
    const choices = getIntervalChoices(card);
    expect(choices[3].minutes).toBe(25);
  });
});

describe('createDefaultSM2', () => {
  beforeEach(() => {
    jest.spyOn(Date, 'now').mockReturnValue(1_000_000);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('returns default SM-2 values', () => {
    const defaults = createDefaultSM2();
    expect(defaults).toEqual({
      interval: 0,
      easeFactor: 2.5,
      repetitions: 0,
      nextReviewTime: 1_000_000,
      lastReviewedAt: null,
    });
  });
});
