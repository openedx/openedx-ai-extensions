import React from 'react';
import PropTypes from 'prop-types';
import { Button, Alert, Card } from '@openedx/paragon';
import {
  Warning,
} from '@openedx/paragon/icons';
import { prepareContextData, callWorkflowService } from '../services';

/**
 * AI Response Component
 * Handles display and interaction with AI responses
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
  // Don't render if no response or error
  if (!response && !error) {
    return null;
  }

  // set response with url
  const baseUrl = window.location.origin;
  const hyperlinkUrl = `${baseUrl}/${response}`;

  const handleClearSession = async () => {
    try {
      // Prepare context data
      const preparedContext = prepareContextData({
        ...contextData,
      });

      // Make API call
      await callWorkflowService({
        context: preparedContext,
        action: 'clear_session',
        payload: {
          requestId: `ai-request-${Date.now()}`,
          courseId: preparedContext.courseId || null,
        },
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[AISidebarResponse] Clear session error:', err);
    }
  };

  const handleClearAndClose = async () => {
    await handleClearSession();
    if (onClear) {
      onClear();
    }
  };

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

          {/* Error state */}
          {error && (
            <Alert
              variant="danger"
              className="py-2 px-3 mb-2"
              dismissible
              onClose={() => onError && onError('')}
            >
              <div className="d-flex align-items-start">
                <Warning className="me-2 mt-1" style={{ width: '16px', height: '16px' }} />
                <small>{error}</small>
              </div>
            </Alert>
          )}

          {/* Success response */}
          {response && !isLoading && (
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
