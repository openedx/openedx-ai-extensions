import { useRef, useCallback, useEffect } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { logError } from '@edx/frontend-platform/logging';
import { pollTaskStatus as pollTaskStatusApi } from '../data/workflowActions';
import messages from '../messages';

export const POLLING_INTERVALS = { INITIAL: 10000, EXTENDED: 30000 };
export const POLLING_TIMEOUTS = { SWITCH_TO_EXTENDED: 2, MAX_DURATION: 5 };
export const MS_TO_MINUTES = 60000;

interface UseAsyncTaskPollingOptions {
  contextData: Record<string, any>;
  courseId: string;
  onComplete: (responseData: any) => void;
  onError: (message: string) => void;
}

export function useAsyncTaskPolling({
  contextData,
  courseId,
  onComplete,
  onError,
}: UseAsyncTaskPollingOptions) {
  const intl = useIntl();
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
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
        const responseData = data.response as any;
        if (responseData && typeof responseData === 'object' && responseData.questionSlots) {
          onComplete(responseData);
        } else {
          onError(intl.formatMessage(messages['ai.library.creator.error.unexpected.format']));
        }
      } else if (data.status === 'error' || data.status === 'timeout' || data.error) {
        stopPolling();
        onError(data.error || data.message || intl.formatMessage(messages['ai.library.creator.error.generate']));
      }
    } catch (err) {
      logError('useAsyncTaskPolling: poll error:', err);
      // Don't stop on a single poll error
    }
  }, [contextData, courseId, onComplete, onError, stopPolling, intl]);

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
        onError(intl.formatMessage(messages['ai.library.creator.error.timeout']));
        return;
      }

      if (elapsedMinutes >= POLLING_TIMEOUTS.SWITCH_TO_EXTENDED && pollCount === 12) {
        stopPolling();
        pollingIntervalRef.current = setInterval(() => pollOnce(taskId), POLLING_INTERVALS.EXTENDED);
        return;
      }

      pollOnce(taskId);
    }, POLLING_INTERVALS.INITIAL);
  }, [pollOnce, stopPolling, onError, intl]);

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  return { startPolling, stopPolling };
}
