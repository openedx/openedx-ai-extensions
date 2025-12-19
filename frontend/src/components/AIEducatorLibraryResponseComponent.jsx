import React, {
  useState, useEffect, useRef, useCallback, useMemo,
} from 'react';
import PropTypes from 'prop-types';
import {
  Button, Alert, Card, Spinner,
} from '@openedx/paragon';
import { Warning } from '@openedx/paragon/icons';
import { prepareContextData, callWorkflowService } from '../services';

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
const AIEducatorLibraryResponseComponent = ({
  response,
  error,
  isLoading,
  onClear,
  onError,
  customMessage,
  titleText,
  hyperlinkText,
  contextData,
}) => {
  // Polling state
  const [isPolling, setIsPolling] = useState(false);
  const [pollingMessage, setPollingMessage] = useState('');
  const [finalResponse, setFinalResponse] = useState('');
  const [pollingError, setPollingError] = useState('');
  const [lastUpdateTime, setLastUpdateTime] = useState(null);

  const pollingIntervalRef = useRef(null);
  const pollingStartTimeRef = useRef(null);

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
    if (!response) return null;
    try {
      const parsed = JSON.parse(response);
      if (parsed.status === 'processing' && parsed.task_id) {
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
        action: 'get_run_status',
        payload: {
          requestId: `ai-poll-${Date.now()}`,
          courseId: taskData.courseId,
          task_id: taskData.task_id,
        },
      });

      setLastUpdateTime(new Date());
      if (data.message) setPollingMessage(data.message);

      // Handle terminal states
      const isSuccess = data.status === 'completed' || data.status === 'success';
      const isFailure = data.status === 'failed' || data.status === 'error';

      if (isSuccess || isFailure) {
        stopPolling();
        setIsPolling(false);

        if (isSuccess) {
          setFinalResponse(extractResponseData(data, 'Task completed successfully'));
        } else {
          setPollingError(data.error || data.message || 'Task failed');
        }
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Error polling task status:', err);
      // Don't stop polling on single error
    }
  }, [stopPolling]);

  /**
   * Start polling for async task status
   * Uses adaptive intervals: initial fast polling, then switches to extended interval
   */
  const startPolling = useCallback((taskData) => {
    pollingStartTimeRef.current = Date.now();
    setIsPolling(true);
    setPollingMessage(taskData.message || 'Processing your request...');
    setFinalResponse('');
    setPollingError('');

    pollTaskStatus(taskData);

    let pollCount = 0;
    pollingIntervalRef.current = setInterval(() => {
      const elapsedMinutes = (Date.now() - pollingStartTimeRef.current) / MS_TO_MINUTES;
      pollCount += 1;

      // Stop after max duration
      if (elapsedMinutes >= POLLING_TIMEOUTS.MAX_DURATION) {
        stopPolling();
        setIsPolling(false);
        setPollingError('Task is taking longer than expected. Please check back later.');
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
  }, [pollTaskStatus, stopPolling]);

  // Effect to handle response changes
  useEffect(() => {
    if (!response) return undefined;

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
    if (!asyncTask?.task_id) return;

    try {
      await callWorkflowService({
        context: prepareContextData({
          ...contextData,
          courseId: asyncTask.courseId,
          locationId: asyncTask.locationId,
        }),
        action: 'cancel_run',
        payload: {
          requestId: `ai-cancel-${Date.now()}`,
          courseId: asyncTask.courseId,
          task_id: asyncTask.task_id,
        },
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[AIResponse] Cancel run error:', err);
    }
  }, [asyncTask, contextData]);

  /**
   * Clear the current session on the backend
   */
  const handleClearSession = useCallback(async () => {
    try {
      await callWorkflowService({
        context: prepareContextData(contextData),
        action: 'clear_session',
        payload: {
          requestId: `ai-request-${Date.now()}`,
        },
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[AIResponse] Clear session error:', err);
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
  if (!response && !error) return null;

  // Build URL for final response link
  const hyperlinkUrl = `${window.location.origin}/${finalResponse}`;

  return (
    <Card className="ai-educator-library-response mt-3 mb-3">
      <Card.Section>
        <div className="ai-library-response-header">
          <h3 className="d-block mb-1" style={{ fontSize: '1.25rem' }}>
            {titleText}
          </h3>
          <small className="d-block mb-2" style={{ fontSize: '0.75rem' }}>
            {customMessage}
          </small>
        </div>

        <div className="ai-response-container mt-2">

          {/* Error state from parent or polling */}
          {(error || pollingError) && (
            <Alert
              variant="danger"
              className="py-2 px-3 mb-2"
              dismissible
              onClose={() => {
                if (onError) { onError(''); }
                setPollingError('');
              }}
            >
              <div className="d-flex align-items-start">
                <Warning className="me-2 mt-1" style={{ width: '16px', height: '16px' }} />
                <small>{error || pollingError}</small>
              </div>
            </Alert>
          )}

          {/* Polling/Processing state */}
          {isPolling && !pollingError && (
            <div className="polling-container">
              <div className="mb-2">
                <div className="d-flex align-items-center justify-content-between mb-1">
                  <div className="d-flex align-items-center">
                    <small className="fw-semibold me-2">Processing...</small>
                    <Spinner animation="border" size="sm" />
                  </div>
                  <button
                    type="button"
                    onClick={handleManualRefresh}
                    className="btn btn-link p-0 text-decoration-none"
                    style={{ fontSize: '0.75rem' }}
                    title={lastUpdateTime ? `Last updated: ${lastUpdateTime.toLocaleTimeString()}` : 'Check status'}
                  >
                    update
                  </button>
                </div>
                {pollingMessage && <small className="d-block text-muted">{pollingMessage}</small>}
              </div>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={handleCancelAndClose}
                className="w-100"
              >
                Cancel
              </Button>
            </div>
          )}

          {/* Success response */}
          {finalResponse && !isLoading && !isPolling && (
            <div className="response-container">
              <div className="mb-2">
                <p className="mb-2" style={{ fontSize: '0.875rem' }}>
                  The generated questions have been added to your Content Library.
                </p>
                <p className="mb-2" style={{ fontSize: '0.875rem' }}>
                  They are saved in an <strong>unpublished</strong> state for you to review before making them
                  available to learners.
                </p>
                {hyperlinkUrl && (
                  <a href={hyperlinkUrl} target="_blank" rel="noopener noreferrer" className="fw-semibold">
                    {hyperlinkText || 'View content ›'}
                  </a>
                )}
              </div>
              {handleClearAndClose && (
                <div className="d-flex justify-content-end mt-3">
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={handleClearAndClose}
                    className="py-1 px-2"
                  >
                    Clear
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

AIEducatorLibraryResponseComponent.propTypes = {
  response: PropTypes.string,
  error: PropTypes.string,
  isLoading: PropTypes.bool,
  onClear: PropTypes.func,
  onError: PropTypes.func,
  customMessage: PropTypes.string,
  titleText: PropTypes.string,
  hyperlinkText: PropTypes.string,
  contextData: PropTypes.shape({}),
};

AIEducatorLibraryResponseComponent.defaultProps = {
  response: null,
  error: null,
  isLoading: false,
  onClear: null,
  onError: null,
  customMessage: 'Question generation success.',
  titleText: 'AI Assistant',
  hyperlinkText: 'View content ›',
  contextData: {},
};

export default AIEducatorLibraryResponseComponent;
