import {
  useState, useCallback, useMemo,
} from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Button, ModalDialog, Spinner,
} from '@openedx/paragon';
import Flashcard from './Flashcard';
import StudyControls from './StudyControls';
import { useStudySession } from '../hooks/useStudySession';
import { calculateNextReview } from '../data/spacedRepetition';
import { saveCardStack, clearSession } from '../data/workflowActions';
import { Flashcard as FlashcardType, CardStack } from '../types';
import messages from '../messages';

export interface FlashcardStudyResponseProps {
  response: any;
  error?: string;
  isLoading?: boolean;
  onClear: () => void;
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

const FlashcardStudyResponse = ({
  response,
  error,
  isLoading,
  onClear,
  customMessage,
  contextData = {},
}: FlashcardStudyResponseProps) => {
  console.debug(response)
  const intl = useIntl();
  const [cards, setCards] = useState<FlashcardType[]>(() => parseCards(response));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  // Re-parse cards when response changes and reopen the modal
  console.debug(isModalOpen)
  useMemo(() => {
    const parsed = parseCards(response);
    if (parsed.length > 0) {
      setCards(parsed);
      if (!response?.fromSession) {
        setIsModalOpen(true);
      }
    }
  }, [response]);

  const {
    currentCard,
    dueCards,
    nextCard,
    reviewedCount,
    nextDueIn,
  } = useStudySession({ cards });

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

    setIsFlipped(false);
    nextCard();
  }, [currentCard, nextCard]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError('');
    try {
      const cardStack: CardStack = {
        cards,
        createdAt: Date.now(),
        lastStudiedAt: Date.now(),
      };
      await saveCardStack({ context: contextData, cardStack });
    } catch {
      setSaveError(intl.formatMessage(messages['ai.extensions.flashcard.error.save']));
    } finally {
      setIsSaving(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleReopen = () => {
    setIsModalOpen(true);
  };

  const handleClearSession = async () => {
    try {
      await clearSession({ context: contextData });
    } catch {
      // Silently fail — still reset the UI
    }
    onClear();
  };

  if (isLoading || (!response && !error)) { return null; }

  if (error) {
    return <Alert variant="danger">{error}</Alert>;
  }

  const hasCards = cards.length > 0;
  const currentIndex = currentCard ? dueCards.indexOf(currentCard) + 1 : 0;

  return (
    <>
      {!hasCards && (
        <Alert
          variant="info"
          actions={[
            <Button onClick={onClear}>
              {intl.formatMessage(messages['ai.extensions.flashcard.creator.display.button'])}
            </Button>,
            <Button variant="outline-primary" onClick={handleClearSession}>
              {intl.formatMessage(messages['ai.extensions.flashcard.study.clear.session'])}
            </Button>,
          ]}
        >
          {intl.formatMessage(messages['ai.extensions.flashcard.study.empty'])}
        </Alert>
      )}

      {hasCards && !isModalOpen && (
        <Alert
          variant="info"
          actions={[
            <Button onClick={handleReopen}>
              {intl.formatMessage(messages['ai.extensions.flashcard.creator.display.button'])}
            </Button>,
            <Button variant="outline-primary" onClick={handleClearSession}>
              {intl.formatMessage(messages['ai.extensions.flashcard.study.clear.session'])}
            </Button>,
          ]}
        >
          {intl.formatMessage(messages['ai.extensions.flashcard.study.paused'])}
        </Alert>
      )}

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
          {/* Progress */}
          <div className="d-flex justify-content-between align-items-center mb-3">
            <small className="text-gray-500">
              {currentCard
                ? intl.formatMessage(messages['ai.extensions.flashcard.study.progress'], {
                  current: currentIndex,
                  total: dueCards.length,
                })
                : intl.formatMessage(messages['ai.extensions.flashcard.study.no.cards.due'])}
            </small>
            <small className="text-gray-500">
              {intl.formatMessage(messages['ai.extensions.flashcard.study.reviewed'], {
                count: reviewedCount,
              })}
            </small>
          </div>

          {/* Card or no-cards-due state */}
          {currentCard ? (
            <>
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
            nextDueIn !== null && nextDueIn > 0 && (
              <p className="text-center text-muted mt-3">
                {intl.formatMessage(messages['ai.extensions.flashcard.study.next.due'], {
                  time: intl.formatRelativeTime(
                    Math.ceil(nextDueIn / 60_000),
                    'minute',
                  ),
                })}
              </p>
            )
          )}

          {saveError && (
            <Alert variant="danger" dismissible onClose={() => setSaveError('')} className="mt-3">
              {saveError}
            </Alert>
          )}
        </ModalDialog.Body>

        <ModalDialog.Footer>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <Spinner animation="border" size="sm" className="mr-2" screenReaderText={intl.formatMessage(messages['ai.extensions.flashcard.study.saving'])} />
                {intl.formatMessage(messages['ai.extensions.flashcard.study.saving'])}
              </>
            ) : (
              intl.formatMessage(messages['ai.extensions.flashcard.study.save.progress'])
            )}
          </Button>
          <ModalDialog.CloseButton variant="tertiary">
            {intl.formatMessage(messages['ai.extensions.flashcard.study.done'])}
          </ModalDialog.CloseButton>
        </ModalDialog.Footer>
      </ModalDialog>
    </>
  );
};

export default FlashcardStudyResponse;
