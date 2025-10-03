import React from 'react';
import PropTypes from 'prop-types';
import { Button, Alert, Collapsible } from '@openedx/paragon';
import {
  Send,
  CheckCircle,
  Warning,
  Download,
} from '@openedx/paragon/icons';

/**
 * AI Response Component
 * Handles display and interaction with AI responses
 */
const AIResponseComponent = ({
  response,
  error,
  isLoading,
  onAskAgain,
  onClear,
  onError,
  showActions = true,
  // allowCopy is defined for prop validation but not currently used in the component
  // eslint-disable-next-line no-unused-vars
  allowCopy,
  allowDownload,
}) => {
  /**
   * Download response as text file
   */
  const handleDownload = () => {
    const blob = new Blob([response], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai-assistance-${new Date().getTime()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /**
   * Format response text for display
   */
  const formatResponse = (text) => {
    if (!text) { return ''; }

    // Convert newlines to break tags
    let formatted = text.replace(/\n/g, '<br>');

    // Basic markdown-like formatting
    formatted = formatted
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>');

    return formatted;
  };

  // Don't render if no response or error
  if (!response && !error) {
    return null;
  }

  return (
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
          <Collapsible
            title={(
              <div className="d-flex align-items-center">
                <CheckCircle className="text-success me-2" style={{ width: '16px', height: '16px' }} />
                <small className="text-success fw-semibold">AI Assistant Response</small>
              </div>
            )}
            defaultOpen
            styling="basic"
          >
            <div
              className="response-content p-3 mt-2 bg-light rounded border-start border-success border-3"
              style={{
                fontSize: '0.9rem',
                lineHeight: '1.5',
              }}
            >
              {/* Response text */}
              <div
                className="response-text"
                // eslint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{
                  __html: formatResponse(response),
                }}
              />

              {/* Action buttons */}
              {showActions && (
                <div className="response-actions d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
                  <small className="text-muted d-flex align-items-center">
                    💡 AI-generated assistance
                  </small>

                  <div className="action-buttons d-flex gap-2">

                    {/* Download button */}
                    {allowDownload && (
                      <Button
                        variant="link"
                        size="sm"
                        onClick={handleDownload}
                        className="p-1 text-muted"
                        title="Download response"
                      >
                        <Download style={{ width: '14px', height: '14px' }} />
                      </Button>
                    )}

                    {/* Clear button */}
                    {onClear && (
                      <Button
                        variant="outline-secondary"
                        size="sm"
                        onClick={onClear}
                        className="py-1 px-2"
                      >
                        Clear
                      </Button>
                    )}

                    {/* Ask again button */}
                    {onAskAgain && (
                      <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={onAskAgain}
                        disabled={isLoading}
                        iconBefore={Send}
                        className="py-1 px-2"
                      >
                        Ask Again
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </Collapsible>
        </div>
      )}
    </div>
  );
};

AIResponseComponent.propTypes = {
  response: PropTypes.string,
  error: PropTypes.string,
  isLoading: PropTypes.bool,
  onAskAgain: PropTypes.func,
  onClear: PropTypes.func,
  onError: PropTypes.func,
  showActions: PropTypes.bool,
  allowCopy: PropTypes.bool,
  allowDownload: PropTypes.bool,
};

AIResponseComponent.defaultProps = {
  response: null,
  error: null,
  isLoading: false,
  onAskAgain: null,
  onClear: null,
  onError: null,
  showActions: true,
  allowCopy: true,
  allowDownload: false,
};

export default AIResponseComponent;
