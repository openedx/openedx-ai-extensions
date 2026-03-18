import {
  useState, useCallback, useEffect, useMemo,
} from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Button, Spinner,
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
  preloadPreviousSession?: boolean;
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
  preloadPreviousSession = false,
}: FlashcardCreatorProps) => {
  const intl = useIntl();
  const [step, setStep] = useState<FlashcardStep>(preloadPreviousSession ? 'loading' : 'idle');
  const [showForm, setShowForm] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const contextData = useMemo(
    () => ({ courseId, locationId, uiSlotSelectorId }),
    [courseId, locationId, uiSlotSelectorId],
  );

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

  // Check for existing session on mount
  useEffect(() => {
    if (!preloadPreviousSession) { return undefined; }

    let cancelled = false;
    const checkSession = async () => {
      try {
        const data = await getSessionResponse({ context: contextData });
        if (cancelled) { return; }
        const cards = data?.cards;
        if (Array.isArray(cards) && cards.length > 0) {
          setResponse({ ...data, fromSession: true });
          setHasAsked(true);
        } else {
          setStep('idle');
        }
      } catch {
        if (!cancelled) { setStep('idle'); }
      }
    };
    checkSession();
    return () => { cancelled = true; };
  }, [contextData, setResponse, setHasAsked, preloadPreviousSession]);

  const handleGenerate = async (numCards: number | null) => {
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

  const handleStartOver = () => {
    stopPolling();
    setStep('idle');
    setShowForm(false);
    setErrorMessage('');
  };

  if (hasAsked) { return null; }

  return (
    <div className="flashcard-creator my-2 py-3 border-bottom d-flex justify-content-between align-items-center flex-wrap">
      {step === 'loading' && (
        <div className="text-center py-3 mx-auto">
          <Spinner animation="border" size="sm" className="mr-2" screenReaderText={intl.formatMessage(messages['ai.extensions.flashcard.creator.loading.session'])} />
          <span className="small">
            {intl.formatMessage(messages['ai.extensions.flashcard.creator.loading.session'])}
          </span>
        </div>
      )}

      {step === 'idle' && (
        <>
          {!showForm && (
            <>
              <small className="d-block mb-2">
                {customMessage || intl.formatMessage(messages['ai.extensions.flashcard.creator.description'])}
              </small>
              <Button
                variant="primary"
                size="sm"
                iconBefore={AutoAwesome}
                onClick={() => setShowForm(true)}
              >
                {buttonText || intl.formatMessage(messages['ai.extensions.flashcard.creator.create.button'])}
              </Button>
            </>
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
        <div className="text-center py-3 mx-auto">
          <Spinner animation="border" size="sm" className="mr-2" screenReaderText={intl.formatMessage(messages['ai.extensions.flashcard.generate.form.generating'])} />
          <span className="small">
            {intl.formatMessage(messages['ai.extensions.flashcard.generate.form.generating'])}
          </span>
        </div>
      )}

      {step === 'error' && (
      <Alert
        variant="danger"
        dismissible
        onClose={handleStartOver}
        className="w-100"
      >{errorMessage}
      </Alert>
      )}
    </div>
  );
};

export default FlashcardCreator;
