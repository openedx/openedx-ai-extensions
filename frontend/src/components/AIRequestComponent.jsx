import React from 'react';
import PropTypes from 'prop-types';
import { Button, Spinner } from '@openedx/paragon';
import { Send } from '@openedx/paragon/icons';

/**
 * AI Request Component
 * Handles the initial request interface and loading state
 */
const AIRequestComponent = ({
  isLoading,
  hasAsked,
  onAskAI,
  customMessage = 'Get personalized AI assistance for this learning unit',
  buttonText = 'Ask AI',
  disabled = false,
}) => {
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
          <small className="text-muted">Analyzing content...</small>
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
            {customMessage}
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
            {buttonText}
          </Button>
        </div>
      )}
    </div>
  );
};

AIRequestComponent.propTypes = {
  isLoading: PropTypes.bool.isRequired,
  hasAsked: PropTypes.bool.isRequired,
  onAskAI: PropTypes.func.isRequired,
  customMessage: PropTypes.string,
  buttonText: PropTypes.string,
  disabled: PropTypes.bool,
};

AIRequestComponent.defaultProps = {
  customMessage: 'Need help understanding this content?',
  buttonText: 'Get AI Assistance',
  disabled: false,
};

export default AIRequestComponent;
