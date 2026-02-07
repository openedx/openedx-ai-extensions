import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Button, Alert, Collapsible } from '@openedx/paragon';
import {
  CheckCircle,
  Warning,
} from '@openedx/paragon/icons';

/**
 * AI Response Component
 * Handles display and interaction with AI responses
 */

interface AIResponseComponentProps {
  response?: string;
  error?: string;
  isLoading?: boolean;
  onClear?: () => void;
  onError?: (error: string) => void;
  customMessage?: string;
}
const AIResponseComponent = ({
  response,
  error,
  isLoading,
  onClear,
  onError,
  customMessage = 'AI Assistant Response',
}: AIResponseComponentProps) => {
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
                <small className="text-success fw-semibold">{customMessage}</small>
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
              <div className="response-text">
                <ReactMarkdown>
                  {response}
                </ReactMarkdown>
              </div>

              {/* Action buttons */}
              <div className="response-actions d-flex justify-content-end align-items-center mt-3 pt-2 border-top gap-2">
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
              </div>
            </div>
          </Collapsible>
        </div>
      )}
    </div>
  );
};

export default AIResponseComponent;
