import React, { useCallback } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { logError } from '@edx/frontend-platform/logging';
import {
  Alert, Button, Card,
  Hyperlink,
} from '@openedx/paragon';
import { prepareContextData } from '../../services';
import { PluginContext } from '../../types';
import { clearSession } from '../data/workflowActions';
import messages from '../messages';

interface LibraryProblemCreatorResponseProps {
  response?: string;
  error?: string;
  isLoading?: boolean;
  onClear?: () => void;
  customMessage?: string;
  titleText?: string;
  hyperlinkText?: string;
  contextData?: PluginContext;
}

const LibraryProblemCreatorResponse = ({
  response,
  error,
  isLoading = false,
  onClear,
  customMessage,
  titleText,
  hyperlinkText,
  contextData = {},
}: LibraryProblemCreatorResponseProps) => {
  const intl = useIntl();

  const displayTitle = titleText || intl.formatMessage(messages['ai.library.creator.response.title']);
  const displayMessage = customMessage || intl.formatMessage(messages['ai.library.creator.response.message']);
  const displayHyperlinkText = hyperlinkText || intl.formatMessage(messages['ai.library.creator.response.hyperlink']);

  const handleClearAndClose = useCallback(async () => {
    try {
      await clearSession({ context: prepareContextData(contextData) });
    } catch (err) {
      logError('LibraryProblemCreatorResponse: clear session error:', err);
    }
    if (onClear) { onClear(); }
  }, [contextData, onClear]);

  if (!response && !error) { return null; }

  const collectionUrl = response ? `${window.location.origin}/${response}` : null;

  return (
    <Card className="library-creator-response mt-3 mb-3">
      <Card.Section>
        <h3 className="d-block mb-1">{displayTitle}</h3>
        <span className="d-block mb-2 x-small">{displayMessage}</span>

        {error && (
          <Alert variant="danger">{error}</Alert>
        )}

        {response && !isLoading && (
          <div className="response-container">
            <p className="small mb-2">
              {intl.formatMessage(messages['ai.library.creator.response.success.detail'])}
            </p>
            {collectionUrl && (
              <Hyperlink
                destination={collectionUrl}
                target="_blank"
                externalLinkAlternativeText={intl.formatMessage(messages['ai.library.creator.response.opens.new.tab'])}
                className="small mb-3"
              >
                {displayHyperlinkText}
              </Hyperlink>
            )}
            <div className="d-flex justify-content-end">
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={handleClearAndClose}
              >
                {intl.formatMessage(messages['ai.library.creator.response.clear'])}
              </Button>
            </div>
          </div>
        )}
      </Card.Section>
    </Card>
  );
};

export default LibraryProblemCreatorResponse;
