import {
  useState, useCallback, useEffect, useMemo, useRef,
} from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Badge, Button, Icon, ModalDialog,
  Stack, StatefulButton,
} from '@openedx/paragon';
import { AutoAwesome, Quiz, SpinnerSimple } from '@openedx/paragon/icons';
import Flashcard from './Flashcard';
import StudyControls from './StudyControls';
import { useStudySession } from '../hooks/useStudySession';
import { useAsyncTaskPolling, POLLING_ERROR_KEYS } from '../hooks/useAsyncTaskPolling';
import { calculateNextReview } from '../utils';
import { saveCardStack, generateFlashcards } from '../data/workflowActions';
import { Flashcard as FlashcardType, CardStack, FlashcardStep } from '../types';
import { prepareContextData } from '../../services';
import LastReviewLabel from './LastReviewLabel';
import messages from '../messages';

export interface FlashcardStudyResponseProps {
  response: any;
  error?: string;
  isLoading?: boolean;
  contextData?: Record<string, any>;
  customMessage?: string;
}

const parseCards = (data: any): FlashcardType[] => {
  if (!data) { return []; }
  if (Array.isArray(data.cards)) { return data.cards; }
  if (Array.isArray(data?.response?.cards)) { return data.response.cards; }
  if (Array.isArray(data)) { return data; }
  return [];
};

const ERROR_MESSAGES: Record<string, keyof typeof messages> = {
  [POLLING_ERROR_KEYS.TIMEOUT]: 'ai.extensions.flashcard.error.timeout',
  [POLLING_ERROR_KEYS.GENERATE]: 'ai.extensions.flashcard.error.generate',
  [POLLING_ERROR_KEYS.NETWORK]: 'ai.extensions.flashcard.error.network',
};

const FlashcardStudyResponse = ({
  response,
  error,
  isLoading,
  customMessage,
  contextData = {},
}: FlashcardStudyResponseProps) => {
  const intl = useIntl();
  const preparedContext = useMemo(() => prepareContextData(contextData), [contextData]);
  const [cards, setCards] = useState<FlashcardType[]>(() => parseCards(response));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFlipped, setIsFlipped] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [step, setStep] = useState<FlashcardStep>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [progressMessage, setProgressMessage] = useState('');
  const isDirtyRef = useRef(false);
  const cardsRef = useRef(cards);
  // Re-parse cards when response changes and reopen the modal
  useMemo(() => {
    const parsed = parseCards(response);
    if (parsed.length > 0) {
      setCards(parsed);
    }
  }, [response]);

  const {
    currentCard,
    dueCards,
    nextCard,
    reviewedCount,
  } = useStudySession({ cards });

  // Keep cardsRef in sync so the auto-save callback always has fresh data
  useEffect(() => { cardsRef.current = cards; }, [cards]);

  // ── Add cards (run_async) ───────────────────────────────────────────────
  const courseId = (contextData as any)?.courseId || '';
  const numCards = response?.numCards ?? null;
  const onAddComplete = useCallback((responseData: any) => {
    const newCards = parseCards(responseData);
    if (newCards.length > 0) {
      setCards((prev) => [...prev, ...newCards]);
      isDirtyRef.current = true;
    }
    setStep('idle');
    setProgressMessage('');
  }, []);

  const onAddError = useCallback((errorKey: string) => {
    setStep('error');
    setProgressMessage('');
    const key = ERROR_MESSAGES[errorKey] || 'ai.extensions.flashcard.error.generate';
    setErrorMessage(intl.formatMessage(messages[key]));
  }, [intl]);

  const onAddProgress = useCallback((message: string) => {
    setProgressMessage(message);
  }, []);

  const { startPolling: startAddPolling } = useAsyncTaskPolling({
    contextData: preparedContext,
    courseId,
    onComplete: onAddComplete,
    onError: onAddError,
    onProgress: onAddProgress,
  });

  const handleAddCards = async () => {
    setStep('generating');
    setErrorMessage('');
    setProgressMessage('');
    try {
      const data = await generateFlashcards({ context: preparedContext, numCards });
      if (data.taskId) {
        startAddPolling(data.taskId);
        if (data.message) { setProgressMessage(data.message); }
      } else {
        onAddComplete(data);
      }
    } catch {
      setStep('error');
      setErrorMessage(intl.formatMessage(messages['ai.extensions.flashcard.error.generate']));
    }
  };

  const handleDismissError = () => {
    setStep('idle');
    setErrorMessage('');
  };

  const autoSave = useCallback(async () => {
    if (!isDirtyRef.current) { return; }
    isDirtyRef.current = false;
    try {
      const cardStack: CardStack = {
        cards: cardsRef.current,
        createdAt: Date.now(),
        lastStudiedAt: Date.now(),
      };
      await saveCardStack({ context: preparedContext, cardStack });
    } catch {
      setSaveError(intl.formatMessage(messages['ai.extensions.flashcard.error.save']));
    }
  }, [preparedContext, intl]);

  // Auto-save when the tab becomes hidden (covers tab switches, screen locks, alt-tabs)
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.hidden) { autoSave(); }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, [autoSave]);

  const handleFlip = useCallback(() => {
    setIsFlipped((prev) => !prev);
  }, []);

  const handleRate = useCallback((quality: number) => {
    if (!currentCard) { return; }

    const result = calculateNextReview(
      quality,
      currentCard.interval,
      currentCard.easeFactor,
      currentCard.repetitions,
    );

    setCards((prev) => prev.map((c) => (c.id === currentCard.id
      ? {
        ...c,
        interval: result.interval,
        easeFactor: result.easeFactor,
        repetitions: result.repetitions,
        nextReviewTime: result.nextReviewTime,
        lastReviewedAt: Date.now(),
      }
      : c)));

    isDirtyRef.current = true;
    setIsFlipped(false);
    nextCard();
  }, [currentCard, nextCard]);

  const handleCloseModal = () => {
    autoSave();
    setIsModalOpen(false);
  };

  const handleReopen = () => {
    setIsModalOpen(true);
  };

  if (isLoading || (!response && !error)) { return null; }

  if (error) {
    return <Alert variant="danger">{error}</Alert>;
  }

  const hasCards = cards.length > 0;
  const currentIndex = currentCard ? dueCards.indexOf(currentCard) + 1 : 0;

  return (
    <>
      <div className="d-flex align-items-center justify-content-end px-3 small flex-wrap">
        <div className="my-2 mw-md-50">
          <span className="pr-md-5">{intl.formatMessage(messages['ai.extensions.flashcard.study.session.description'])}</span>
          <LastReviewLabel cards={cards} />
        </div>
        <Stack gap={2} direction="horizontal">
          {hasCards && (
            <Button size="sm" onClick={handleReopen} iconBefore={Quiz}>
              <span>{intl.formatMessage(messages['ai.extensions.flashcard.creator.display.button'])}</span>
              {dueCards.length > 0 && (
                <>
                  <Badge variant="primary" className="ml-2 border py-1">{dueCards.length}</Badge>
                  <span className="sr-only">{intl.formatMessage(messages['ai.extensions.flashcard.creator.display.button.due'])}</span>
                </>
              )}
            </Button>
          )}
          <StatefulButton
            variant="outline-primary"
            size="sm"
            onClick={handleAddCards}
            state={step}
            labels={{
              idle: intl.formatMessage(messages['ai.extensions.flashcard.study.clear.session']),
              loading: intl.formatMessage(messages['ai.extensions.flashcard.creator.loading']),
              generating: progressMessage || intl.formatMessage(messages['ai.extensions.flashcard.generating']),
            }}
            icons={{
              idle: <Icon src={AutoAwesome} />,
              generating: <Icon src={SpinnerSimple} className="icon-spin" />,
            }}
            disabledStates={['loading', 'generating']}
          />
        </Stack>
        {step === 'error' && errorMessage && (
          <Alert variant="danger" dismissible onClose={handleDismissError} className="mt-3">
            {errorMessage}
          </Alert>
        )}
      </div>

      <ModalDialog
        title={customMessage || intl.formatMessage(messages['ai.extensions.flashcard.title'])}
        isOpen={hasCards && isModalOpen}
        onClose={handleCloseModal}
        size="lg"
        isFullscreenOnMobile
        isOverflowVisible={false}
        className="flashcard-study-modal"
      >
        <ModalDialog.Header>
          <ModalDialog.Title>
            {customMessage || intl.formatMessage(messages['ai.extensions.flashcard.title'])}
          </ModalDialog.Title>
        </ModalDialog.Header>

        <ModalDialog.Body>
          {currentCard ? (
            <>
              {/* Progress */}
              <div className="d-flex justify-content-between align-items-center mb-3">
                <small className="text-gray-500">
                  {intl.formatMessage(messages['ai.extensions.flashcard.study.progress'], {
                    current: currentIndex,
                    total: dueCards.length,
                  })}
                </small>
                <small className="text-gray-500">
                  {intl.formatMessage(messages['ai.extensions.flashcard.study.reviewed'], {
                    count: reviewedCount,
                  })}
                </small>
              </div>

              <Flashcard
                question={currentCard.question}
                answer={currentCard.answer}
                isFlipped={isFlipped}
                onFlip={handleFlip}
              />
              <div className={isFlipped ? '' : 'invisible'}>
                <StudyControls card={currentCard} onRate={handleRate} />
              </div>
            </>
          ) : (
            <div className="text-center py-4">
              <h4>{intl.formatMessage(messages['ai.extensions.flashcard.study.no.cards.due'])}</h4>
              <p className="text-muted">
                {intl.formatMessage(messages['ai.extensions.flashcard.study.no.cards.due.description'])}
              </p>
              {reviewedCount > 0 && (
                <small className="text-gray-500">
                  {intl.formatMessage(messages['ai.extensions.flashcard.study.reviewed'], {
                    count: reviewedCount,
                  })}
                </small>
              )}
            </div>
          )}

        </ModalDialog.Body>

        <ModalDialog.Footer>
          <ModalDialog.CloseButton variant="tertiary">
            {intl.formatMessage(messages['ai.extensions.flashcard.study.done'])}
          </ModalDialog.CloseButton>
        </ModalDialog.Footer>
      </ModalDialog>

      {saveError && (
        <Alert
          variant="danger"
          dismissible
          onClose={() => setSaveError('')}
          className="mt-3"
          actions={[
            <Button variant="primary" onClick={() => { setSaveError(''); isDirtyRef.current = true; autoSave(); }}>
              {intl.formatMessage(messages['ai.extensions.flashcard.error.save.retry'])}
            </Button>,
          ]}
        >
          {saveError}
        </Alert>
      )}
    </>
  );
};

export default FlashcardStudyResponse;
