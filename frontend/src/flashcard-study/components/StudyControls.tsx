import { useMemo } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Button, ButtonGroup } from '@openedx/paragon';
import { Flashcard } from '../types';
import { getIntervalChoices } from '../utils';
import messages from '../messages';

export interface StudyControlsProps {
  card: Flashcard;
  onRate: (quality: number) => void;
}

const RATING_METADATA: Record<number, { labelKey: keyof typeof messages }> = {
  1: { labelKey: 'ai.extensions.flashcard.controls.again' },
  2: { labelKey: 'ai.extensions.flashcard.controls.hard' },
  3: { labelKey: 'ai.extensions.flashcard.controls.good' },
  5: { labelKey: 'ai.extensions.flashcard.controls.easy' },
};

const StudyControls = ({ card, onRate }: StudyControlsProps) => {
  const intl = useIntl();
  const choices = useMemo(() => getIntervalChoices(card), [card]);

  return (
    <ButtonGroup size="sm" className="w-100 my-3">
      {choices.map((choice) => {
        const metadata = RATING_METADATA[choice.quality];
        if (!metadata) { return null; }

        const { relativeTime } = choice;
        const intervalLabel = intl.formatRelativeTime(relativeTime.value, relativeTime.unit);

        return (
          <Button
            key={choice.quality}
            variant="outline-primary"
            onClick={() => onRate(choice.quality)}
            className="d-flex flex-column align-items-center"
          >
            <span>
              {intl.formatMessage(messages[metadata.labelKey])}
            </span>
            <span className="x-small">
              {intervalLabel}
            </span>
          </Button>
        );
      })}
    </ButtonGroup>
  );
};

export default StudyControls;
