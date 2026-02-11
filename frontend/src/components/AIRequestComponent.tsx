import React from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Button, Spinner } from '@openedx/paragon';
import { Send } from '@openedx/paragon/icons';
import messages from '../messages';

/**
 * AI Request Component
 * Handles the initial request interface and loading state
 */

interface AIRequestComponentProps {
  isLoading: boolean;
  hasAsked: boolean;
  onAskAI: () => void;
  customMessage?: string;
  buttonText?: string;
  disabled: boolean;
}

const AIRequestComponent = ({
  isLoading,
  hasAsked,
  onAskAI,
  customMessage,
  buttonText,
  disabled = false,
}: AIRequestComponentProps) => {
  const intl = useIntl();

  const displayMessage = customMessage || intl.formatMessage(messages['ai.extensions.request.default.message']);
  const displayButtonText = buttonText || intl.formatMessage(messages['ai.extensions.request.default.button']);

  // Don't render if already asked or currently loading
  if (hasAsked && !isLoading) {
    return null;
  }

  return (
    <div className="ai-request-container">
      {/* Loading state */}
      {isLoading && (
        <div className="d-flex align-items-center justify-content-center py-3">
          <Spinner
            animation="border"
            variant="primary"
            size="sm"
            className="me-2"
          />
          <small className="text-muted">
            {intl.formatMessage(messages['ai.extensions.request.analyzing'])}
          </small>
        </div>
      )}

      {/* Initial request state */}
      {!hasAsked && !isLoading && (
        <div className="d-flex align-items-center justify-content-end">
          <small
            className="text-muted me-3"
            style={{
              paddingRight: '16px',
            }}
          >
            {displayMessage}
          </small>
          <Button
            variant="primary"
            size="sm"
            onClick={onAskAI}
            disabled={disabled || isLoading}
            iconBefore={Send}
            style={{
              borderRadius: '20px',
              fontWeight: '500',
              paddingLeft: '16px',
              paddingRight: '16px',
            }}
          >
            {displayButtonText}
          </Button>
        </div>
      )}
    </div>
  );
};

export default AIRequestComponent;
