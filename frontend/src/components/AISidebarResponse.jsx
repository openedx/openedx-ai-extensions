import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Button, Alert, IconButton } from '@openedx/paragon';
import {
  Send,
  CheckCircle,
  Warning,
  Close,
} from '@openedx/paragon/icons';

/**
 * AI Sidebar Response Component
 * Displays AI responses in a floating right sidebar
 */
const AISidebarResponse = ({
  response,
  error,
  isLoading,
  onAskAgain,
  onClear,
  onError,
  showActions = true,
  customMessage,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Show sidebar when response or error arrives
  useEffect(() => {
    if (response || error) {
      setIsOpen(true);
    }
  }, [response, error]);

  /**
   * Format response text for display
   */
  const formatResponse = (responseText) => {
    if (!responseText) { return ''; }

    // Convert newlines to break tags
    let formatted = responseText.replace(/\n/g, '<br>');

    // Basic markdown-like formatting
    formatted = formatted
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>');

    return formatted;
  };

  /**
   * Clear response and close sidebar (shows request component again)
   */
  const handleClearAndClose = () => {
    setIsOpen(false);
    if (onClear) {
      onClear();
    }
  };

  // Don't render if no response or error
  if (!response && !error) {
    return null;
  }

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            zIndex: 1040,
            transition: 'opacity 0.3s ease',
          }}
          onClick={handleClearAndClose}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Escape' && handleClearAndClose()}
          aria-label="Close sidebar"
        />
      )}

      {/* Sidebar */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: isOpen ? 0 : '-400px',
          width: '400px',
          maxWidth: '90vw',
          height: '100vh',
          backgroundColor: '#fff',
          boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.15)',
          zIndex: 1050,
          transition: 'right 0.3s ease',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #dee2e6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#f8f9fa',
          }}
        >
          <div className="d-flex align-items-center">
            <CheckCircle className="text-success me-2" style={{ width: '20px', height: '20px' }} />
            <strong style={{ fontSize: '1rem' }}>{customMessage || 'AI Assistant Response'}</strong>
          </div>
          <IconButton
            src={Close}
            iconAs="svg"
            alt="Close"
            onClick={handleClearAndClose}
            size="sm"
            variant="secondary"
          />
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {/* Error state */}
          {error && (
            <Alert
              variant="danger"
              className="mb-3"
              dismissible
              onClose={() => onError && onError('')}
            >
              <div className="d-flex align-items-start">
                <Warning className="me-2 mt-1" style={{ width: '16px', height: '16px' }} />
                <div>{error}</div>
              </div>
            </Alert>
          )}

          {/* Success response */}
          {response && !isLoading && (
            <div
              className="response-text"
              style={{
                fontSize: '0.95rem',
                lineHeight: '1.6',
                color: '#212529',
              }}
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{
                __html: formatResponse(response),
              }}
            />
          )}

          {/* Loading state */}
          {isLoading && (
            <div className="text-center py-4">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="text-muted mt-2 mb-0">Generating response...</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {showActions && (response || error) && (
          <div
            style={{
              padding: '16px 20px',
              borderTop: '1px solid #dee2e6',
              backgroundColor: '#f8f9fa',
            }}
          >
            <div className="d-flex justify-content-between align-items-center">
              <small className="text-muted">💡 AI-generated assistance</small>

              <div className="d-flex gap-2">
                {/* Clear button */}
                {onClear && (
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={handleClearAndClose}
                    className="py-1 px-2"
                  >
                    Clear
                  </Button>
                )}

                {/* Ask again button */}
                {onAskAgain && (
                  <Button
                    variant="primary"
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
          </div>
        )}
      </div>
    </>
  );
};

AISidebarResponse.propTypes = {
  response: PropTypes.string,
  error: PropTypes.string,
  isLoading: PropTypes.bool,
  onAskAgain: PropTypes.func,
  onClear: PropTypes.func,
  onError: PropTypes.func,
  showActions: PropTypes.bool,
  customMessage: PropTypes.string,
};

AISidebarResponse.defaultProps = {
  response: null,
  error: null,
  isLoading: false,
  onAskAgain: null,
  onClear: null,
  onError: null,
  showActions: true,
  customMessage: 'AI Assistant Response',
};

export default AISidebarResponse;
