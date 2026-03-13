import { useState, useCallback, useMemo } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Button, Spinner, Stack,
} from '@openedx/paragon';
import Flashcard from './Flashcard';
import StudyControls from './StudyControls';
import { useStudySession } from '../hooks/useStudySession';
import { calculateNextReview } from '../data/spacedRepetition';
import { saveCardStack } from '../data/workflowActions';
import { Flashcard as FlashcardType, CardStack } from '../types';
import messages from '../messages';

export interface FlashcardStudyResponseProps {
  response: any;
  error?: string;
  isLoading?: boolean;
  onClear: () => void;
  contextData?: Record<string, any>;
}

const parseCards = (response: any): FlashcardType[] => {
  if (!response) { return []; }
  if (Array.isArray(response.cards)) { return response.cards; }
  if (Array.isArray(response)) { return response; }
  return [];
};

const FlashcardStudyResponse = ({
  response,
  error,
  isLoading,
  onClear,
  contextData = {},
}: FlashcardStudyResponseProps) => {
  const intl = useIntl();
  const [cards, setCards] = useState<FlashcardType[]>(() => parseCards(response));
  const [isFlipped, setIsFlipped] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  // Re-parse cards when response changes
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

  if (!response && !error) { return null; }

  if (isLoading) { return null; }

  if (error) {
    return (
      <Alert variant="danger">
        {error}
      </Alert>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="flashcard-study-response mt-3">
        <Alert variant="info">
          {intl.formatMessage(messages['ai.extensions.flashcard.study.empty'])}
        </Alert>
        <Button variant="outline-secondary" size="sm" onClick={onClear}>
          {intl.formatMessage(messages['ai.extensions.flashcard.study.back'])}
        </Button>
      </div>
    );
  }

  const currentIndex = currentCard
    ? dueCards.indexOf(currentCard) + 1
    : 0;

  return (
    <div className="flashcard-study-response mt-3">
      {/* Progress bar */}
      <div className="d-flex justify-content-between align-items-center mb-2">
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

      {/* Current card or empty state */}
      {currentCard ? (
        <>
          <Flashcard
            question={currentCard.question}
            answer={currentCard.answer}
            isFlipped={isFlipped}
            onFlip={handleFlip}
          />
          {isFlipped && (
            <StudyControls card={currentCard} onRate={handleRate} />
          )}
        </>
      ) : (
        <>
          {nextDueIn !== null && nextDueIn > 0 && (
            <p className="text-center text-muted mt-3">
              {intl.formatMessage(messages['ai.extensions.flashcard.study.next.due'], {
                time: intl.formatRelativeTime(
                  Math.ceil(nextDueIn / 60_000),
                  'minute',
                ),
              })}
            </p>
          )}
        </>
      )}

      {/* Save and back actions */}
      {saveError && (
        <Alert variant="danger" dismissible onClose={() => setSaveError('')} className="mt-2">
          {saveError}
        </Alert>
      )}

      <Stack direction="horizontal" gap={2} className="mt-3">
        <Button
          variant="primary"
          size="sm"
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
        <Button variant="outline-secondary" size="sm" onClick={onClear}>
          {intl.formatMessage(messages['ai.extensions.flashcard.study.back'])}
        </Button>
      </Stack>
    </div>
  );
};

export default FlashcardStudyResponse;
