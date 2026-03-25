import {
  useState, useCallback, useEffect, useMemo, useRef,
} from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Alert, Icon, StatefulButton } from '@openedx/paragon';
import { AutoAwesome, SpinnerSimple } from '@openedx/paragon/icons';
import { POLLING_ERROR_KEYS, useAsyncTaskPolling } from '../hooks/useAsyncTaskPolling';
import { generateFlashcards, getSessionResponse } from '../data/workflowActions';
import { prepareContextData } from '../../services';
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
  const numCardsRef = useRef<number | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [progressMessage, setProgressMessage] = useState('');

  const contextData = useMemo(
    () => prepareContextData({ courseId, locationId, uiSlotSelectorId }),
    [courseId, locationId, uiSlotSelectorId],
  );

  const onComplete = useCallback((responseData: any) => {
    setStep('idle');
    setProgressMessage('');
    setResponse({ cards: responseData, numCards: numCardsRef.current });
    setHasAsked(true);
  }, [setResponse, setHasAsked]);

  const onError = useCallback((errorKey: string) => {
    setStep('error');
    setProgressMessage('');
    const messageKey = ERROR_MESSAGES[errorKey] || 'ai.extensions.flashcard.error.generate';
    setErrorMessage(intl.formatMessage(messages[messageKey]));
  }, [intl]);

  const onProgress = useCallback((message: string) => {
    setProgressMessage(message);
  }, []);

  const { startPolling, stopPolling } = useAsyncTaskPolling({
    contextData,
    courseId,
    onComplete,
    onError,
    onProgress,
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

  const handleGenerate = async (selectedNumCards: number | null) => {
    numCardsRef.current = selectedNumCards;
    setShowForm(false);
    setStep('generating');
    setProgressMessage('');
    try {
      const data = await generateFlashcards({ context: contextData, numCards: selectedNumCards });
      if (data.taskId) {
        startPolling(data.taskId);
        if (data.message) { setProgressMessage(data.message); }
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
    setErrorMessage('');
    setProgressMessage('');
  };

  if (hasAsked) { return null; }

  return (
    <div className="flashcard-creator d-flex align-items-center justify-content-end px-3 small flex-wrap">

      { (!errorMessage && showForm) ? (
        <GenerateForm onGenerate={handleGenerate} isLoading={false} />
      ) : (
        <>
          <small className="d-block my-2 pr-md-5 container-mw-xs">
            {customMessage || intl.formatMessage(messages['ai.extensions.flashcard.creator.description'])}
          </small>
          <StatefulButton
            variant="primary"
            size="sm"
            state={step}
            onClick={() => setShowForm(!showForm)}
            labels={{
              default: buttonText || intl.formatMessage(messages['ai.extensions.flashcard.creator.create.button']),
              generating: progressMessage || intl.formatMessage(messages['ai.extensions.flashcard.generating']),
              loading: intl.formatMessage(messages['ai.extensions.flashcard.creator.loading']),
            }}
            icons={{
              default: <Icon src={AutoAwesome} />,
              generating: <Icon src={SpinnerSimple} className="icon-spin" />,
              loading: <Icon src={SpinnerSimple} className="icon-spin" />,
            }}
            disabledStates={['loading', 'generating']}
          />
        </>
      )}
      {
        step === 'error' && (
          <Alert
            variant="danger"
            dismissible
            onClose={handleStartOver}
            className="w-100"
          >{errorMessage}
          </Alert>
        )
      }
    </div>
  );
};

export default FlashcardCreator;
