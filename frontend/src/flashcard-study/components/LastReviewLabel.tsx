import { useEffect, useReducer } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Flashcard } from '../types';
import { toRelativeTime } from '../utils';
import messages from '../messages';

const REFRESH_INTERVAL = 30_000;

interface LastReviewLabelProps {
  cards: Flashcard[];
}

const LastReviewLabel = ({ cards }: LastReviewLabelProps) => {
  const intl = useIntl();
  const [, forceUpdate] = useReducer((x: number) => x + 1, 0);

  useEffect(() => {
    const id = setInterval(forceUpdate, REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, []);

  const lastReview = Math.max(...cards.map((c) => c.lastReviewedAt ?? 0));
  if (lastReview <= 0) { return null; }

  const minutesAgo = Math.floor((Date.now() - lastReview) / 60_000);
  let lastReviewText: string;
  if (minutesAgo < 1) {
    lastReviewText = intl.formatMessage(messages['ai.extensions.flashcard.study.paused.session.justNow']);
  } else {
    const { value, unit } = toRelativeTime(minutesAgo);
    lastReviewText = intl.formatMessage(messages['ai.extensions.flashcard.study.paused.session.lastReview'], {
      time: intl.formatRelativeTime(-value, unit),
    });
  }

  return (
    <small className="d-block text-muted">{lastReviewText}</small>
  );
};

export default LastReviewLabel;
