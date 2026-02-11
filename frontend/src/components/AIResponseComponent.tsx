import React from 'react';
import ReactMarkdown from 'react-markdown';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Button, Alert, Collapsible, Card,
} from '@openedx/paragon';
import {
  CheckCircle,
  Warning,
} from '@openedx/paragon/icons';
import messages from '../messages';

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
  customMessage,
}: AIResponseComponentProps) => {
  const intl = useIntl();
  const displayMessage = customMessage || intl.formatMessage(messages['ai.extensions.response.default.title']);

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
                <small className="text-success fw-semibold">{displayMessage}</small>
              </div>
            )}
            defaultOpen
            styling="basic"
          >
            <Card variant="muted">
              {/* Response text */}
              <Card.Section>
                <ReactMarkdown>
                  {response}
                </ReactMarkdown>
              </Card.Section>
              {/* Action buttons */}
              {/* Clear button */}
              {onClear && (
                <>
                  <Card.Divider />
                  <Card.Footer className="pt-3">
                    <Button
                      variant="outline-secondary"
                      size="sm"
                      onClick={onClear}
                      className="py-1 px-2"
                    >
                      {intl.formatMessage(messages['ai.extensions.response.clear'])}
                    </Button>
                  </Card.Footer>
                </>
              )}
            </Card>
          </Collapsible>
        </div>
      )}
    </div>
  );
};

export default AIResponseComponent;
