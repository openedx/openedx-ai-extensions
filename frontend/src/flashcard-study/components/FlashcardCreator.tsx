import { useState, useCallback } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Button, Card, Spinner, Stack,
} from '@openedx/paragon';
import { AutoAwesome } from '@openedx/paragon/icons';
import { POLLING_ERROR_KEYS, useAsyncTaskPolling } from '../hooks/useAsyncTaskPolling';
import { generateFlashcards, getSessionResponse } from '../data/workflowActions';
import GenerateForm from './GenerateForm';
import messages from '../messages';
import { FlashcardStep } from '../types';

const ERROR_MESSAGES: Record<string, keyof typeof messages> = {
  [POLLING_ERROR_KEYS.TIMEOUT]: 'ai.extensions.flashcard.error.timeout',
  [POLLING_ERROR_KEYS.GENERATE]: 'ai.extensions.flashcard.error.generate',
  [POLLING_ERROR_KEYS.NETWORK]: 'ai.extensions.flashcard.error.network',
};

export interface FlashcardCreatorProps {
  hasAsked: boolean;
  setResponse: (response: any) => void;
  setHasAsked: (hasAsked: boolean) => void;
  courseId?: string;
  locationId?: string;
  uiSlotSelectorId?: string;
  buttonText?: string;
  customMessage?: string;
}

const FlashcardCreator = ({
  hasAsked,
  setResponse,
  setHasAsked,
  courseId = '',
  locationId = '',
  uiSlotSelectorId = '',
  buttonText,
  customMessage,
}: FlashcardCreatorProps) => {
  const intl = useIntl();
  const [step, setStep] = useState<FlashcardStep>('idle');
  const [showForm, setShowForm] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const contextData = { courseId, locationId, uiSlotSelectorId };

  const onComplete = useCallback((responseData: any) => {
    setStep('idle');
    setResponse(responseData);
    setHasAsked(true);
  }, [setResponse, setHasAsked]);

  const onError = useCallback((errorKey: string) => {
    setStep('error');
    const messageKey = ERROR_MESSAGES[errorKey] || 'ai.extensions.flashcard.error.generate';
    setErrorMessage(intl.formatMessage(messages[messageKey]));
  }, [intl]);

  const { startPolling, stopPolling } = useAsyncTaskPolling({
    contextData,
    courseId,
    onComplete,
    onError,
  });

  const handleGenerate = async (numCards: number) => {
    setStep('generating');
    setShowForm(false);
    try {
      const data = await generateFlashcards({ context: contextData, numCards });
      if (data.taskId) {
        startPolling(data.taskId);
      } else {
        setResponse(data);
        setHasAsked(true);
        setStep('idle');
      }
    } catch {
      setStep('error');
      setErrorMessage(intl.formatMessage(messages['ai.extensions.flashcard.error.generate']));
    }
  };

  const handleDisplayCards = async () => {
    setStep('generating');
    try {
      const data = await getSessionResponse({ context: contextData });
      setResponse(data);
      setHasAsked(true);
      setStep('idle');
    } catch {
      setStep('error');
      setErrorMessage(intl.formatMessage(messages['ai.extensions.flashcard.error.load']));
    }
  };

  const handleStartOver = () => {
    stopPolling();
    setStep('idle');
    setShowForm(false);
    setErrorMessage('');
  };

  if (hasAsked) { return null; }

  return (
    <Card className="flashcard-creator mt-3 mb-3">
      <Card.Section>
        <h3 className="d-block mb-1">
          {intl.formatMessage(messages['ai.extensions.flashcard.title'])}
        </h3>
        <small className="d-block mb-2 x-small">
          {customMessage || intl.formatMessage(messages['ai.extensions.flashcard.creator.description'])}
        </small>

        {step === 'idle' && (
          <>
            {!showForm && (
              <Stack gap={2}>
                <Button
                  variant="outline-primary"
                  size="sm"
                  className="w-100"
                  iconBefore={AutoAwesome}
                  onClick={() => setShowForm(true)}
                >
                  {buttonText || intl.formatMessage(messages['ai.extensions.flashcard.creator.create.button'])}
                </Button>
                <Button
                  variant="outline-primary"
                  size="sm"
                  className="w-100"
                  onClick={handleDisplayCards}
                >
                  {intl.formatMessage(messages['ai.extensions.flashcard.creator.display.button'])}
                </Button>
              </Stack>
            )}

            {showForm && (
              <GenerateForm
                onGenerate={handleGenerate}
                isLoading={false}
              />
            )}
          </>
        )}

        {step === 'generating' && (
          <div className="text-center py-3">
            <Spinner animation="border" size="sm" className="mr-2" screenReaderText={intl.formatMessage(messages['ai.extensions.flashcard.generate.form.generating'])} />
            <span className="small">
              {intl.formatMessage(messages['ai.extensions.flashcard.generate.form.generating'])}
            </span>
          </div>
        )}

        {step === 'error' && (
          <>
            <Alert variant="danger">{errorMessage}</Alert>
            <Button
              variant="outline-secondary"
              size="sm"
              className="w-100"
              onClick={handleStartOver}
            >
              {intl.formatMessage(messages['ai.extensions.flashcard.creator.start.over'])}
            </Button>
          </>
        )}
      </Card.Section>
    </Card>
  );
};

export default FlashcardCreator;
