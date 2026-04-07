import { useIntl } from '@edx/frontend-platform/i18n';
import { Button, Card } from '@openedx/paragon';

import messages from '../messages';

import './Flashcard.scss';

export interface FlashcardProps {
  question: string;
  answer: string;
  isFlipped: boolean;
  onFlip: () => void;
}

const Flashcard = ({
  question,
  answer,
  isFlipped,
  onFlip,
}: FlashcardProps) => {
  const intl = useIntl();

  return (
    <div className="flashcard-scene p-2">
      <div
        className={`flashcard-stage ${isFlipped ? 'flashcard-stage--flipped' : ''}`}
        aria-live="polite"
      >
        {/* Question face */}
        <Card className="flashcard-face flashcard-face--front bg-light-200 h-100 rounded-lg" inert={isFlipped ? '' : undefined}>
          <Card.Section className="d-flex flex-column align-items-center justify-content-center h-100">
            <span className="x-small text-uppercase font-weight-bold text-gray-500 mb-2">
              {intl.formatMessage(messages['ai.extensions.flashcard.card.question.label'])}
            </span>
            <p className="lead text-center mb-0">{question}</p>
            <Button
              id="flashcard-flip-to-answer-btn"
              variant="primary"
              size="sm"
              className="mt-3"
              onClick={onFlip}
            >
              {intl.formatMessage(messages['ai.extensions.flashcard.card.show.answer'])}
            </Button>
          </Card.Section>
        </Card>

        {/* Answer face */}
        <Card className="flashcard-face flashcard-face--back bg-light-300 h-100 rounded-lg" inert={!isFlipped ? '' : undefined}>
          <Card.Section className="d-flex flex-column align-items-center justify-content-center h-100">
            <span className="x-small text-uppercase font-weight-bold text-gray-500 mb-2">
              {intl.formatMessage(messages['ai.extensions.flashcard.card.answer.label'])}
            </span>
            <p className="lead text-center mb-0">{answer}</p>
            <Button
              id="flashcard-flip-to-question-btn"
              variant="outline-primary"
              size="sm"
              className="mt-3"
              onClick={onFlip}
            >
              {intl.formatMessage(messages['ai.extensions.flashcard.card.show.question'])}
            </Button>
          </Card.Section>
        </Card>
      </div>
    </div>
  );
};

export default Flashcard;
