import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWrapper as render } from '../../setupTest';
import StudyControls from './StudyControls';
import { Flashcard } from '../types';

const mockCard: Flashcard = {
  id: '1',
  question: 'What is React?',
  answer: 'A JavaScript library for building user interfaces',
  nextReviewTime: 1000,
  interval: 10,
  easeFactor: 2.5,
  repetitions: 2,
  lastReviewedAt: null,
};

describe('StudyControls', () => {
  it('renders four rating buttons with correct labels and intervals', () => {
    render(<StudyControls card={mockCard} onRate={jest.fn()} />);

    expect(screen.getByRole('button', { name: /again/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /hard/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /good/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /easy/i })).toBeInTheDocument();

    // intl.formatRelativeTime renders full localized strings
    // repetitions=2 -> Again(1min), Hard(12min), Good(25min), Easy(33min)
    expect(screen.getByText('in 1 minute')).toBeInTheDocument();
    expect(screen.getByText('in 12 minutes')).toBeInTheDocument();
    expect(screen.getByText('in 25 minutes')).toBeInTheDocument();
    expect(screen.getByText('in 33 minutes')).toBeInTheDocument();
  });

  it('calls onRate with correct quality when buttons are clicked', async () => {
    const user = userEvent.setup();
    const onRate = jest.fn();
    render(<StudyControls card={mockCard} onRate={onRate} />);

    await user.click(screen.getByRole('button', { name: /again/i }));
    expect(onRate).toHaveBeenCalledWith(1);

    await user.click(screen.getByRole('button', { name: /hard/i }));
    expect(onRate).toHaveBeenCalledWith(2);

    await user.click(screen.getByRole('button', { name: /good/i }));
    expect(onRate).toHaveBeenCalledWith(3);

    await user.click(screen.getByRole('button', { name: /easy/i }));
    expect(onRate).toHaveBeenCalledWith(5);
  });
});
