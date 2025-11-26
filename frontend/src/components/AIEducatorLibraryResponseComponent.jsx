import React from 'react';
import PropTypes from 'prop-types';
import { Button, Alert, Card } from '@openedx/paragon';
import {
  CheckCircle,
  Warning,
} from '@openedx/paragon/icons';

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
}) => {
  // Don't render if no response or error
  if (!response && !error) {
    return null;
  }

  // set response with url
  const baseUrl = window.location.origin;
  const hyperlinkUrl = `${baseUrl}/${response}`;

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
              <div className="d-flex align-items-center mb-2">
                <CheckCircle className="text-success me-2" style={{ width: '16px', height: '16px' }} />
                <small className="text-success">
                  {customMessage}{' '}
                  {hyperlinkUrl && (
                    <a href={hyperlinkUrl} target="_blank" rel="noopener noreferrer" className="fw-semibold">
                      {hyperlinkText || 'View content'}
                    </a>
                  )}
                </small>
              </div>
              {onClear && (
                <div className="d-flex justify-content-between align-items-center">
                  <small className="text-muted fst-italic" style={{ fontSize: '0.7rem' }}>
                    *Note: The generated questions are not published.
                  </small>
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={onClear}
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
};

AIEducatorLibraryResponseComponent.defaultProps = {
  response: null,
  error: null,
  isLoading: false,
  onClear: null,
  onError: null,
  customMessage: 'You can find the generated questions in your content library.',
  titleText: 'AI Assistant',
  hyperlinkText: 'View content',
};

export default AIEducatorLibraryResponseComponent;
