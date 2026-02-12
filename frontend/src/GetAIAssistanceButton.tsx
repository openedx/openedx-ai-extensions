import React, { useState, useCallback } from 'react';

// Import service modules
import {
  prepareContextData,
  callWorkflowService,
  formatErrorMessage,
} from './services';

// Import UI components
import {
  AIRequestComponent,
  AIResponseComponent,
} from './components';
import { WORKFLOW_ACTIONS } from './constants';

interface GetAIAssistanceButtonProps {
  requestMessage?: string;
  buttonText?: string;
}

/**
 * Main AI Assistant Plugin Component
 * Orchestrates the AI assistance flow using modular components
 */
const GetAIAssistanceButton = ({
  requestMessage = 'Need help understanding this content?',
  buttonText = 'Get AI Assistance',
  ...props
}: GetAIAssistanceButtonProps) => {
  // Core state management
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState('');
  const [error, setError] = useState('');
  const [hasAsked, setHasAsked] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);

  /**
   * Handle AI assistant request
   * Now completely flexible - works with any available context
   * Streaming logic
   */
  const handleAskAI = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setResponse('');
    // DON'T set hasAsked to true here - only set it on success

    try {
      // Prepare context data - captures everything available
      const contextData = prepareContextData({
        ...props,
      });

      let buffer = '';
      // Make API call with flexible parameters
      const data = await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.SIMPLE_BUTTON_ASSISTANCE,
          requestId: `ai-request-${Date.now()}`,
        },
        onStreamChunk: (chunk) => {
          setIsLoading(false);
          setHasAsked(true);
          buffer += chunk;
          setResponse(buffer);
        },
      });

      if (data.requestId) { setRequestId(data.requestId); }
      if (data.response) {
        setResponse(data.response);
        setHasAsked(true); // Only set hasAsked on successful response
      } else if (data.message) {
        setResponse(data.message);
        setHasAsked(true);
      } else if (data.content) {
        setResponse(data.content);
        setHasAsked(true);
      } else if (data.result) {
        setResponse(data.result);
        setHasAsked(true);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        // If API returns something but in unexpected format, try to use it
        setResponse(JSON.stringify(data, null, 2));
        setHasAsked(true);
      }

      // Set final accumulated response text
      setResponse(data.response || buffer);
      setHasAsked(true);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('AI Assistant Error:', err);
      setError(formatErrorMessage(err));
      // DON'T set hasAsked to true on error - keep button available
    } finally {
      setIsLoading(false);
    }
  }, [props]);

  /**
   * Reset component state for new request
   */
  const handleReset = useCallback(() => {
    setResponse('');
    setError('');
    setHasAsked(false);
    setRequestId(null);
  }, []);

  /**
   * Clear error state but keep button available
   */
  const handleClearError = useCallback((errorMessage = '') => {
    setError(errorMessage);
    // Don't change hasAsked state when clearing errors
  }, []);

  // Debug info for development
  const debugInfo = process.env.NODE_ENV === 'development' ? {
    requestId,
    hasAsked,
    hasError: !!error,
  } : null;

  return (
    <div className="ai-assistant-plugin" style={{ maxWidth: '100%' }}>

      {/* Request Interface - Show button unless we have a successful response */}
      <AIRequestComponent
        isLoading={isLoading}
        hasAsked={hasAsked && !error} // Only hide if successful AND no error
        onAskAI={handleAskAI}
        customMessage={requestMessage}
        buttonText={buttonText}
        disabled={false} // Never disable - let API decide what to do
      />

      {/* Response Interface */}
      <AIResponseComponent
        response={response}
        error={error}
        isLoading={isLoading}
        onClear={handleReset}
        onError={handleClearError}
      />

      {/* Development debug info */}
      {debugInfo && (
        <details className="mt-2">
          <summary className="text-muted" style={{ fontSize: '0.8rem' }}>
            Debug Info (Development Only)
          </summary>
          <pre className="text-muted mt-1" style={{ fontSize: '0.7rem' }}>
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

export default GetAIAssistanceButton;
