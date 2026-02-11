import React, {
  useState, useEffect, useRef, useCallback, useMemo,
} from 'react';
import { logError } from '@edx/frontend-platform/logging';
import { useIntl, FormattedMessage } from '@edx/frontend-platform/i18n';
import {
  Button, Alert, Card, Spinner,
} from '@openedx/paragon';
import { Warning } from '@openedx/paragon/icons';
import { prepareContextData, callWorkflowService } from '../services';
import { PluginContext } from '../types';
import { WORKFLOW_ACTIONS } from '../constants';
import messages from '../messages';

// Polling configuration
const POLLING_INTERVALS = {
  INITIAL: 10000, // 10 seconds
  EXTENDED: 30000, // 30 seconds
};

const POLLING_TIMEOUTS = {
  SWITCH_TO_EXTENDED: 2, // minutes
  MAX_DURATION: 5, // minutes
};

const MS_TO_MINUTES = 60000; // Milliseconds in a minute

/**
 * AI Response Component
 * Handles display and interaction with AI responses
 * Manages polling for async tasks
 */

interface AIEducatorLibraryResponseComponentProps {
  response?: string;
  error?: string;
  isLoading?: boolean;
  onClear?: () => void;
  onError?: (error: any) => void;
  customMessage?: string;
  titleText?: string;
  hyperlinkText?: string;
  contextData?: PluginContext;
}

const AIEducatorLibraryResponseComponent = ({
  response,
  error,
  isLoading = false,
  onClear,
  onError,
  customMessage,
  titleText,
  hyperlinkText,
  contextData = {},
}: AIEducatorLibraryResponseComponentProps) => {
  const intl = useIntl();
  // Polling state
  const [isPolling, setIsPolling] = useState(false);
  const [pollingMessage, setPollingMessage] = useState('');
  const [finalResponse, setFinalResponse] = useState('');
  const [pollingError, setPollingError] = useState('');
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollingStartTimeRef = useRef<number | null>(null);

  // Default display values
  const displayTitle = titleText || intl.formatMessage(messages['ai.extensions.educator.title']);
  const displayCustomMessage = customMessage || intl.formatMessage(messages['ai.extensions.educator.success.message']);
  const displayHyperlinkText = hyperlinkText || intl.formatMessage(messages['ai.extensions.educator.hyperlink.text']);

  /**
   * Stop the polling interval if active
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  /**
   * Reset all polling-related state to initial values
   */
  const resetPollingState = useCallback(() => {
    setIsPolling(false);
    setPollingMessage('');
    setFinalResponse('');
    setPollingError('');
  }, []);

  /**
   * Extract response content with fallback chain
   * Tries: response -> result -> message -> fallback
   */
  const extractResponseData = (data, fallback = '') => (
    data.response || data.result || data.message || fallback
  );

  // Memoized async task data from response
  const asyncTask = useMemo(() => {
    if (!response) { return null; }
    try {
      const parsed = JSON.parse(response);
      if (parsed.status === 'processing' && parsed.taskId) {
        return parsed;
      }
    } catch (e) {
      // Not JSON or not an async task
    }
    return null;
  }, [response]);

  /**
   * Poll for async task status and update state accordingly
   */
  const pollTaskStatus = useCallback(async (taskData) => {
    try {
      const contextPayload = prepareContextData({
        courseId: taskData.courseId,
        locationId: taskData.locationId,
      });

      const data = await callWorkflowService({
        context: contextPayload,
        payload: {
          action: WORKFLOW_ACTIONS.GET_RUN_STATUS,
          requestId: `ai-poll-${Date.now()}`,
          courseId: taskData.courseId,
          taskId: taskData.taskId,
        },
      });

      setLastUpdateTime(new Date());
      if (data.message) { setPollingMessage(data.message); }

      // Handle terminal states
      const isSuccess = data.status === 'completed' || data.status === 'success';
      const isFailure = data.status === 'failed' || data.status?.includes('error') || data?.error;

      if (isSuccess || isFailure) {
        stopPolling();
        setIsPolling(false);

        if (isSuccess) {
          setFinalResponse(extractResponseData(data, intl.formatMessage(messages['ai.extensions.educator.task.completed'])));
        } else {
          setPollingError(data.error || data.message || intl.formatMessage(messages['ai.extensions.educator.task.failed']));
        }
      }
    } catch (err) {
      logError('Error polling task status:', err);
      // Don't stop polling on single error
    }
  }, [stopPolling, intl]);

  /**
   * Start polling for async task status
   * Uses adaptive intervals: initial fast polling, then switches to extended interval
   */
  const startPolling = useCallback((taskData) => {
    pollingStartTimeRef.current = Date.now();
    setIsPolling(true);
    setPollingMessage(taskData.message || intl.formatMessage(messages['ai.extensions.educator.task.processing']));
    setFinalResponse('');
    setPollingError('');

    pollTaskStatus(taskData);

    let pollCount = 0;
    pollingIntervalRef.current = setInterval(() => {
      if (pollingStartTimeRef.current === null) {
        return;
      }
      const elapsedMinutes = (Date.now() - pollingStartTimeRef.current) / MS_TO_MINUTES;
      pollCount += 1;

      // Stop after max duration
      if (elapsedMinutes >= POLLING_TIMEOUTS.MAX_DURATION) {
        stopPolling();
        setIsPolling(false);
        setPollingError(intl.formatMessage(messages['ai.extensions.educator.task.timeout']));
        return;
      }

      // Switch to slower polling after initial period (12 polls × 10s = 2 min)
      if (elapsedMinutes >= POLLING_TIMEOUTS.SWITCH_TO_EXTENDED && pollCount === 12) {
        stopPolling();
        pollingIntervalRef.current = setInterval(() => {
          pollTaskStatus(taskData);
        }, POLLING_INTERVALS.EXTENDED);
        return;
      }

      pollTaskStatus(taskData);
    }, POLLING_INTERVALS.INITIAL);
  }, [pollTaskStatus, stopPolling, intl]);

  // Effect to handle response changes
  useEffect(() => {
    if (!response) { return undefined; }

    if (asyncTask) {
      startPolling(asyncTask);
    } else {
      setFinalResponse(response);
    }

    return () => stopPolling();
  }, [response, asyncTask, startPolling, stopPolling]);

  /**
   * Manually refresh task status on demand
   */
  const handleManualRefresh = useCallback(() => {
    if (asyncTask) {
      pollTaskStatus(asyncTask);
    }
  }, [asyncTask, pollTaskStatus]);

  /**
   * Cancel the currently running async task
   */
  const handleCancelRun = useCallback(async () => {
    if (!asyncTask?.taskId) { return; }

    try {
      await callWorkflowService({
        context: prepareContextData({
          ...contextData,
          courseId: asyncTask.courseId,
          locationId: asyncTask.locationId,
        }),
        payload: {
          action: WORKFLOW_ACTIONS.CANCEL_RUN,
          requestId: `ai-cancel-${Date.now()}`,
          courseId: asyncTask.courseId,
          taskId: asyncTask.taskId,
        },
      });
    } catch (err) {
      logError('[AIResponse] Cancel run error:', err);
    }
  }, [asyncTask, contextData]);

  /**
   * Clear the current session on the backend
   */
  const handleClearSession = useCallback(async () => {
    try {
      await callWorkflowService({
        context: prepareContextData(contextData),
        payload: {
          action: WORKFLOW_ACTIONS.CLEAR_SESSION,
          requestId: `ai-request-${Date.now()}`,
        },
      });
    } catch (err) {
      logError('[AIResponse] Clear session error:', err);
    }
  }, [contextData]);

  /**
   * Unified handler for closing and cleaning up
   * @param {boolean} shouldCancelRun - Whether to cancel the running task first
   */
  const handleClose = useCallback(async (shouldCancelRun = false) => {
    // Cancel the run if requested
    if (shouldCancelRun) {
      await handleCancelRun();
    }

    // Clear polling and reset state
    stopPolling();
    resetPollingState();

    await handleClearSession();
    if (onClear) {
      onClear();
    }
  }, [handleCancelRun, handleClearSession, onClear, stopPolling, resetPollingState]);

  // Convenience wrappers for specific close scenarios
  const handleCancelAndClose = useCallback(() => handleClose(true), [handleClose]);
  const handleClearAndClose = useCallback(() => handleClose(false), [handleClose]);

  // Early return if nothing to display
  if (!response && !error) { return null; }

  // Build URL for final response link
  const hyperlinkUrl = `${window.location.origin}/${finalResponse}`;

  return (
    <Card className="ai-educator-library-response mt-3 mb-3">
      <Card.Section>
        <div className="ai-library-response-header">
          <h3 className="d-block mb-1">
            {displayTitle}
          </h3>
          <span className="d-block mb-2 x-small">
            {displayCustomMessage}
          </span>
        </div>

        <div className="ai-response-container mt-2">

          {/* Error state from parent or polling */}
          {(error || pollingError) && (
            <Alert
              variant="danger"
              dismissible
              onClose={() => {
                if(onError) (onError(error))
                handleClose()}}
              icon={Warning}
            >
              {error || pollingError}
            </Alert>
          )}

          {/* Polling/Processing state */}
          {isPolling && !pollingError && (
            <div className="polling-container">
              <div className="d-flex align-items-center justify-content-between mb-2">
                <div className="d-flex align-items-center">
                  <Spinner animation="border" size="sm" role="status" />
                  {pollingMessage && <small className="ml-2 d-block text-muted x-small">{pollingMessage}</small>}
                </div>
                <Button
                  onClick={handleManualRefresh}
                  size="sm"
                  variant="link"
                  title={intl.formatMessage(messages['ai.extensions.educator.last.updated'], { time: lastUpdateTime?.toLocaleTimeString() || '' })}
                >
                  {intl.formatMessage(messages['ai.extensions.educator.update.button'])}
                </Button>
              </div>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={handleCancelAndClose}
                className="w-100"
              >
                {intl.formatMessage(messages['ai.extensions.educator.cancel'])}
              </Button>
            </div>
          )}

          {/* Success response */}
          {finalResponse && !isLoading && !isPolling && (
            <div className="response-container">
              <div className="mb-2 x-small">
                <p className="mb-2">
                  <FormattedMessage {...messages['ai.extensions.educator.success.text']} values={{ br: <br /> }} />
                </p>
                {hyperlinkUrl && (
                  <a href={hyperlinkUrl} target="_blank" rel="noopener noreferrer">
                    {displayHyperlinkText}
                  </a>
                )}
              </div>
              {handleClearAndClose && (
                <div className="d-flex justify-content-end">
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={handleClearAndClose}
                  >
                    {intl.formatMessage(messages['ai.extensions.response.clear'])}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </Card.Section>
    </Card>
  );
};

export default AIEducatorLibraryResponseComponent;
