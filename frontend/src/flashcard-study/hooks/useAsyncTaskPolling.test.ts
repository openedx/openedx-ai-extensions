import { renderHook, act } from '@testing-library/react';
import { pollTaskStatus } from '../data/workflowActions';
import {
  useAsyncTaskPolling, POLLING_INTERVALS, POLLING_TIMEOUTS, MS_TO_MINUTES, POLLING_ERROR_KEYS,
} from './useAsyncTaskPolling';

jest.mock('@edx/frontend-platform/logging', () => ({
  logError: jest.fn(),
}));

jest.mock('../data/workflowActions', () => ({
  pollTaskStatus: jest.fn(),
}));

const mockPoll = pollTaskStatus as jest.Mock;
const contextData = {
  courseId: 'course-v1:Org+Course+Run',
  locationId: 'block-v1:Org+Course+Run+type@unit+block@abc',
  uiSlotSelectorId: 'openedx.learning.unit.header.slot.v1',
};
const courseId = 'course-v1:Org+Course+Run';

describe('useAsyncTaskPolling', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockPoll.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('calls pollTaskStatus immediately on startPolling', async () => {
    mockPoll.mockResolvedValue({ status: 'processing' });
    const onComplete = jest.fn();
    const onError = jest.fn();

    const { result } = renderHook(() => useAsyncTaskPolling({
      contextData, courseId, onComplete, onError,
    }));

    await act(async () => {
      result.current.startPolling('task-1');
    });

    expect(mockPoll).toHaveBeenCalledWith({
      context: contextData,
      taskId: 'task-1',
      courseId,
    });
  });

  it('calls onComplete when status is completed', async () => {
    const responseData = { cards: [{ id: '1', question: 'Q', answer: 'A' }] };
    mockPoll.mockResolvedValue({ status: 'completed', response: responseData });
    const onComplete = jest.fn();
    const onError = jest.fn();

    const { result } = renderHook(() => useAsyncTaskPolling({
      contextData, courseId, onComplete, onError,
    }));

    await act(async () => {
      result.current.startPolling('task-1');
    });

    expect(onComplete).toHaveBeenCalledWith(responseData);
    expect(onError).not.toHaveBeenCalled();
  });

  it('calls onError with generate key when status is error', async () => {
    mockPoll.mockResolvedValue({ status: 'error', error: 'Something went wrong' });
    const onComplete = jest.fn();
    const onError = jest.fn();

    const { result } = renderHook(() => useAsyncTaskPolling({
      contextData, courseId, onComplete, onError,
    }));

    await act(async () => {
      result.current.startPolling('task-1');
    });

    expect(onError).toHaveBeenCalledWith(POLLING_ERROR_KEYS.GENERATE, 'Something went wrong');
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('calls onError with timeout key after MAX_DURATION minutes', async () => {
    mockPoll.mockResolvedValue({ status: 'processing' });
    const onComplete = jest.fn();
    const onError = jest.fn();
    const now = Date.now();
    jest.spyOn(Date, 'now').mockReturnValue(now);

    const { result } = renderHook(() => useAsyncTaskPolling({
      contextData, courseId, onComplete, onError,
    }));

    await act(async () => {
      result.current.startPolling('task-1');
    });

    jest.spyOn(Date, 'now').mockReturnValue(now + POLLING_TIMEOUTS.MAX_DURATION * MS_TO_MINUTES + 1000);

    await act(async () => {
      jest.advanceTimersByTime(POLLING_INTERVALS.INITIAL);
    });

    expect(onError).toHaveBeenCalledWith(POLLING_ERROR_KEYS.TIMEOUT);
  });

  it('calls onError with network key on poll exception', async () => {
    mockPoll.mockRejectedValue(new Error('Network error'));
    const onComplete = jest.fn();
    const onError = jest.fn();

    const { result } = renderHook(() => useAsyncTaskPolling({
      contextData, courseId, onComplete, onError,
    }));

    await act(async () => {
      result.current.startPolling('task-1');
    });

    expect(onError).toHaveBeenCalledWith(POLLING_ERROR_KEYS.NETWORK, 'Network error');
  });

  it('stopPolling clears the interval', async () => {
    mockPoll.mockResolvedValue({ status: 'processing' });
    const onComplete = jest.fn();
    const onError = jest.fn();

    const { result } = renderHook(() => useAsyncTaskPolling({
      contextData, courseId, onComplete, onError,
    }));

    await act(async () => {
      result.current.startPolling('task-1');
    });

    mockPoll.mockClear();

    act(() => {
      result.current.stopPolling();
    });

    await act(async () => {
      jest.advanceTimersByTime(POLLING_INTERVALS.INITIAL);
    });

    expect(mockPoll).not.toHaveBeenCalled();
  });
});
