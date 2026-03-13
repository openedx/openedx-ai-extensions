import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWrapper as render } from '../../setupTest';
import FlashcardStudyResponse from './FlashcardStudyResponse';
import { saveCardStack } from '../data/workflowActions';
import { Flashcard } from '../types';

jest.mock('../data/workflowActions', () => ({
  saveCardStack: jest.fn(),
}));

const makeDueCard = (overrides: Partial<Flashcard> = {}): Flashcard => ({
  id: '1',
  question: 'What is React?',
  answer: 'A JavaScript library for building user interfaces',
  nextReviewTime: 0,
  interval: 10,
  easeFactor: 2.5,
  repetitions: 2,
  lastReviewedAt: null,
  ...overrides,
});

const makeFutureCard = (overrides: Partial<Flashcard> = {}): Flashcard => ({
  ...makeDueCard(),
  id: '2',
  question: 'What is JSX?',
  answer: 'A syntax extension for JavaScript',
  nextReviewTime: Date.now() + 600_000,
  ...overrides,
});

const defaultProps = {
  response: null as any,
  onClear: jest.fn(),
  contextData: {
    courseId: 'course-v1:Test+101+2024',
    locationId: 'block-v1:Test+101+2024+type@vertical+block@abc',
    uiSlotSelectorId: 'openedx.learning.unit.header.slot.v1',
  },
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('FlashcardStudyResponse', () => {
  describe('when there is no response yet', () => {
    it('renders nothing', () => {
      const { container } = render(<FlashcardStudyResponse {...defaultProps} />);
      expect(container).toBeEmptyDOMElement();
    });

    it('renders nothing while loading', () => {
      const { container } = render(
        <FlashcardStudyResponse {...defaultProps} isLoading />,
      );
      expect(container).toBeEmptyDOMElement();
    });
  });

  describe('when there is an error', () => {
    it('shows the error message', () => {
      render(
        <FlashcardStudyResponse {...defaultProps} error="Something went wrong" />,
      );
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });
  });

  describe('when the response has no cards', () => {
    it('shows an empty state message', () => {
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [] }} />,
      );
      expect(screen.getByText(/no flashcards found/i)).toBeInTheDocument();
    });
  });

  describe('when the modal opens with cards', () => {
    it('shows the modal with the title', () => {
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('AI Flashcard Study')).toBeInTheDocument();
    });

    it('shows the question side of the card with progress', () => {
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.getByText('What is React?')).toBeInTheDocument();
      expect(screen.getByText(/card 1 of 1/i)).toBeInTheDocument();
      expect(screen.getByText(/0 reviewed/i)).toBeInTheDocument();
    });

    it('shows a Done button in the footer', () => {
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument();
    });
  });

  describe('when the user studies a due card', () => {
    it('shows the answer after clicking Show Answer', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /show answer/i }));

      expect(screen.getByText('A JavaScript library for building user interfaces')).toBeInTheDocument();
    });

    it('shows rating controls only after flipping to the answer', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      // Controls are in the DOM but invisible before flipping
      expect(screen.getByRole('button', { name: /again/i }).closest('.invisible')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /show answer/i }));

      expect(screen.getByRole('button', { name: /again/i }).closest('.invisible')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /hard/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /good/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /easy/i })).toBeInTheDocument();
    });

    it('advances to the next card after rating', async () => {
      const user = userEvent.setup();
      const cards = [
        makeDueCard({ id: '1', question: 'Q1', answer: 'A1' }),
        makeDueCard({ id: '2', question: 'Q2', answer: 'A2' }),
      ];
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards }} />,
      );

      await user.click(screen.getByRole('button', { name: /show answer/i }));
      await user.click(screen.getByRole('button', { name: /again/i }));

      expect(screen.getByText('Q2')).toBeInTheDocument();
      expect(screen.getByText(/1 reviewed/i)).toBeInTheDocument();
    });

    it('flips back to the question side after rating', async () => {
      const user = userEvent.setup();
      const cards = [
        makeDueCard({ id: '1', question: 'Q1', answer: 'A1' }),
        makeDueCard({ id: '2', question: 'Q2', answer: 'A2' }),
      ];
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards }} />,
      );

      await user.click(screen.getByRole('button', { name: /show answer/i }));
      await user.click(screen.getByRole('button', { name: /again/i }));

      // Controls are hidden again after rating (card flipped back to question)
      expect(screen.getByRole('button', { name: /again/i }).closest('.invisible')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /show answer/i })).toBeInTheDocument();
    });
  });

  describe('when no cards are due', () => {
    it('shows the no cards due message when all cards are in the future', () => {
      const card = makeFutureCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.getByText(/no cards are due for review/i)).toBeInTheDocument();
    });

    it('shows when the next card will be due', () => {
      const card = makeFutureCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.getByText(/next card due/i)).toBeInTheDocument();
    });
  });

  describe('when the user saves progress', () => {
    it('saves the card stack to the session', async () => {
      const user = userEvent.setup();
      (saveCardStack as jest.Mock).mockResolvedValue({});
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /save progress/i }));

      await waitFor(() => {
        expect(saveCardStack).toHaveBeenCalledWith({
          context: defaultProps.contextData,
          cardStack: expect.objectContaining({
            cards: expect.arrayContaining([expect.objectContaining({ id: '1' })]),
          }),
        });
      });
    });

    it('disables the save button while saving', async () => {
      const user = userEvent.setup();
      (saveCardStack as jest.Mock).mockReturnValue(new Promise(() => {}));
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /save progress/i }));

      expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled();
    });

    it('shows an error when saving fails', async () => {
      const user = userEvent.setup();
      (saveCardStack as jest.Mock).mockRejectedValue(new Error('fail'));
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /save progress/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to save progress/i)).toBeInTheDocument();
      });
    });

    it('re-enables the save button after a failed save', async () => {
      const user = userEvent.setup();
      (saveCardStack as jest.Mock).mockRejectedValue(new Error('fail'));
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /save progress/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save progress/i })).toBeEnabled();
      });
    });
  });

  describe('when the user closes the modal', () => {
    it('calls onClear when the Done button is clicked', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /^done$/i }));
      expect(defaultProps.onClear).toHaveBeenCalled();
    });
  });

  describe('response parsing', () => {
    it('handles response as an array of cards', () => {
      const cards = [makeDueCard()];
      render(
        <FlashcardStudyResponse {...defaultProps} response={cards} />,
      );

      expect(screen.getByText('What is React?')).toBeInTheDocument();
    });

    it('handles response as an object with cards property', () => {
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.getByText('What is React?')).toBeInTheDocument();
    });
  });
});
