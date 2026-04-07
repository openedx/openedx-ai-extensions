import { useRef, useCallback, useEffect } from 'react';
import { logError } from '@edx/frontend-platform/logging';
import { pollTaskStatus as pollTaskStatusApi } from '../data/workflowActions';

export const POLLING_INTERVALS = { INITIAL: 10000, EXTENDED: 30000 };
export const POLLING_TIMEOUTS = { SWITCH_TO_EXTENDED: 2, MAX_DURATION: 5 };
export const MS_TO_MINUTES = 60000;

export const POLLING_ERROR_KEYS = {
  TIMEOUT: 'timeout',
  GENERATE: 'generate',
  NETWORK: 'network',
} as const;

interface UseAsyncTaskPollingOptions {
  contextData: Record<string, any>;
  courseId: string;
  onComplete: (responseData: any) => void;
  onError: (errorKey: string, detail?: string) => void;
  onProgress?: (message: string) => void;
}

/**
 * Polls the backend for the status of an async workflow task.
 *
 * Starts with an initial polling interval (10s) and switches to an extended
 * interval (30s) after 2 minutes. Aborts with a timeout error after 5 minutes.
 * On network failures the polling stops and reports a `'network'` error key;
 * on backend-reported errors it reports a `'generate'` key — both with an
 * optional detail string so the UI can map them to i18n messages.
 *
 * @param options.contextData - Workflow context (courseId, locationId, uiSlotSelectorId).
 * @param options.courseId    - Course identifier forwarded to the poll request.
 * @param options.onComplete  - Called with the response payload when the task succeeds.
 * @param options.onError     - Called with `'timeout'`, `'generate'`, or `'network'` and an optional detail.
 * @param options.onProgress  - Called with the backend message on each in-progress poll response.
 * @returns startPolling - Begins polling for the given `taskId`.
 * @returns stopPolling  - Cancels any active polling interval.
 */
export const useAsyncTaskPolling = ({
  contextData,
  courseId,
  onComplete,
  onError,
  onProgress,
}: UseAsyncTaskPollingOptions) => {
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollingStartTimeRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const pollOnce = useCallback(async (taskId: string) => {
    try {
      const data = await pollTaskStatusApi({ context: contextData, taskId, courseId });

      if (data.status === 'completed' || data.status === 'success') {
        stopPolling();
        onComplete(data.response);
      } else if (data.status === 'error' || data.status === 'timeout' || data.error) {
        stopPolling();
        onError(POLLING_ERROR_KEYS.GENERATE, data.error || data.message);
      } else if (data.message && onProgress) {
        onProgress(data.message);
      }
    } catch (err) {
      logError('useAsyncTaskPolling: poll error:', err);
      stopPolling();
      onError(POLLING_ERROR_KEYS.NETWORK, (err as Error).message);
    }
  }, [contextData, courseId, onComplete, onError, onProgress, stopPolling]);

  const startPolling = useCallback((taskId: string) => {
    pollingStartTimeRef.current = Date.now();
    pollOnce(taskId);

    let pollCount = 0;
    pollingIntervalRef.current = setInterval(() => {
      if (!pollingStartTimeRef.current) { return; }
      const elapsedMinutes = (Date.now() - pollingStartTimeRef.current) / MS_TO_MINUTES;
      pollCount += 1;

      if (elapsedMinutes >= POLLING_TIMEOUTS.MAX_DURATION) {
        stopPolling();
        onError(POLLING_ERROR_KEYS.TIMEOUT);
        return;
      }

      if (elapsedMinutes >= POLLING_TIMEOUTS.SWITCH_TO_EXTENDED && pollCount === 12) {
        stopPolling();
        pollingIntervalRef.current = setInterval(() => pollOnce(taskId), POLLING_INTERVALS.EXTENDED);
        return;
      }

      pollOnce(taskId);
    }, POLLING_INTERVALS.INITIAL);
  }, [pollOnce, stopPolling, onError]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  return { startPolling, stopPolling };
};
