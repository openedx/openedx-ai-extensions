import { useMemo } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Flashcard } from '../types';
import { toRelativeTime } from '../utils';
import messages from '../messages';

interface LastReviewLabelProps {
  cards: Flashcard[];
}

const LastReviewLabel = ({ cards }: LastReviewLabelProps) => {
  const intl = useIntl();

  const lastReviewText = useMemo(() => {
    const lastReview = Math.max(...cards.map((c) => c.lastReviewedAt ?? 0));
    if (lastReview <= 0) { return null; }
    const minutesAgo = Math.round((Date.now() - lastReview) / 60_000);
    if (minutesAgo < 1) {
      return intl.formatMessage(messages['ai.extensions.flashcard.study.paused.session.justNow']);
    }
    const { value, unit } = toRelativeTime(minutesAgo);
    return intl.formatMessage(messages['ai.extensions.flashcard.study.paused.session.lastReview'], {
      time: intl.formatRelativeTime(-value, unit),
    });
  }, [cards, intl]);

  return (
    <small className="d-block text-muted">{lastReviewText}</small>
  );
};

export default LastReviewLabel;
