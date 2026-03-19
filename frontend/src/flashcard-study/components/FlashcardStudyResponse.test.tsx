import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWrapper as render } from '../../setupTest';
import FlashcardStudyResponse from './FlashcardStudyResponse';
import { saveCardStack, clearSession } from '../data/workflowActions';
import { Flashcard } from '../types';

jest.mock('../data/workflowActions', () => ({
  saveCardStack: jest.fn().mockResolvedValue({}),
  clearSession: jest.fn().mockResolvedValue({}),
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
  (saveCardStack as jest.Mock).mockResolvedValue({});
  (clearSession as jest.Mock).mockResolvedValue({});
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
    it('shows an empty state with display cards and clear session buttons', () => {
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [] }} />,
      );
      expect(screen.getByText(/no flashcards found/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /let's practice/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /generate new set/i })).toBeInTheDocument();
    });

    it('calls onClear when display cards is clicked', async () => {
      const user = userEvent.setup();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [] }} />,
      );
      await user.click(screen.getByRole('button', { name: /let's practice/i }));
      expect(defaultProps.onClear).toHaveBeenCalled();
    });

    it('clears the backend session and resets when clear session is clicked', async () => {
      const user = userEvent.setup();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [] }} />,
      );
      await user.click(screen.getByRole('button', { name: /generate new set/i }));

      await waitFor(() => {
        expect(clearSession).toHaveBeenCalledWith({ context: defaultProps.contextData });
        expect(defaultProps.onClear).toHaveBeenCalled();
      });
    });
  });

  describe('when cards are available but modal is closed', () => {
    it('does not open the modal automatically', () => {
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('shows the practice prompt with action buttons', () => {
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      expect(screen.getByRole('button', { name: /let's practice/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /generate new set/i })).toBeInTheDocument();
    });

    it('opens the modal when the user clicks let\'s practice', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /let's practice/i }));

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('AI Flashcard Study')).toBeInTheDocument();
    });
  });

  describe('when the modal is open with cards', () => {
    const openModal = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByRole('button', { name: /let's practice/i }));
    };

    it('shows the question side of the card with progress', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      expect(screen.getByText('What is React?')).toBeInTheDocument();
      expect(screen.getByText(/card 1 of 1/i)).toBeInTheDocument();
      expect(screen.getByText(/0 reviewed/i)).toBeInTheDocument();
    });

    it('shows a Done button in the footer', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument();
    });
  });

  describe('when the user studies a due card', () => {
    const openModal = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByRole('button', { name: /let's practice/i }));
    };

    it('shows the answer after clicking Show Answer', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /show answer/i }));

      expect(screen.getByText('A JavaScript library for building user interfaces')).toBeInTheDocument();
    });

    it('shows rating controls only after flipping to the answer', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

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
      await openModal(user);

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
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /show answer/i }));
      await user.click(screen.getByRole('button', { name: /again/i }));

      // Controls are hidden again after rating (card flipped back to question)
      expect(screen.getByRole('button', { name: /again/i }).closest('.invisible')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /show answer/i })).toBeInTheDocument();
    });
  });

  describe('when no cards are due', () => {
    const openModal = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByRole('button', { name: /let's practice/i }));
    };

    it('shows a caught-up message when all cards are in the future', async () => {
      const user = userEvent.setup();
      const card = makeFutureCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      expect(screen.getByText(/you're all caught up/i)).toBeInTheDocument();
      expect(screen.getByText(/your memory of this unit is fresh/i)).toBeInTheDocument();
    });
  });

  describe('auto-save', () => {
    const openModal = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByRole('button', { name: /let's practice/i }));
    };

    it('saves automatically when the modal is closed after rating a card', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /show answer/i }));
      await user.click(screen.getByRole('button', { name: /good/i }));
      await user.click(screen.getByRole('button', { name: /^done$/i }));

      await waitFor(() => {
        expect(saveCardStack).toHaveBeenCalledWith({
          context: defaultProps.contextData,
          cardStack: expect.objectContaining({
            cards: expect.arrayContaining([expect.objectContaining({ id: '1' })]),
          }),
        });
      });
    });

    it('does not save when closing without any rating', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /^done$/i }));

      expect(saveCardStack).not.toHaveBeenCalled();
    });

    it('saves when the tab becomes hidden after rating', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /show answer/i }));
      await user.click(screen.getByRole('button', { name: /good/i }));

      Object.defineProperty(document, 'hidden', { value: true, writable: true });
      document.dispatchEvent(new Event('visibilitychange'));

      await waitFor(() => {
        expect(saveCardStack).toHaveBeenCalled();
      });

      Object.defineProperty(document, 'hidden', { value: false, writable: true });
    });

    it('does not save on visibilitychange when nothing has changed', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      Object.defineProperty(document, 'hidden', { value: true, writable: true });
      document.dispatchEvent(new Event('visibilitychange'));

      expect(saveCardStack).not.toHaveBeenCalled();

      Object.defineProperty(document, 'hidden', { value: false, writable: true });
    });

    it('shows an error with retry button when auto-save fails on close', async () => {
      const user = userEvent.setup();
      (saveCardStack as jest.Mock).mockRejectedValue(new Error('fail'));
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /show answer/i }));
      await user.click(screen.getByRole('button', { name: /good/i }));
      await user.click(screen.getByRole('button', { name: /^done$/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to save progress/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });

    it('retries saving when the retry button is clicked', async () => {
      const user = userEvent.setup();
      (saveCardStack as jest.Mock).mockRejectedValueOnce(new Error('fail')).mockResolvedValueOnce({});
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /show answer/i }));
      await user.click(screen.getByRole('button', { name: /good/i }));
      await user.click(screen.getByRole('button', { name: /^done$/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /retry/i }));

      await waitFor(() => {
        expect(saveCardStack).toHaveBeenCalledTimes(2);
        expect(screen.queryByText(/failed to save progress/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('when the user closes the modal', () => {
    const openModal = async (user: ReturnType<typeof userEvent.setup>) => {
      await user.click(screen.getByRole('button', { name: /let's practice/i }));
    };

    it('hides the modal and shows paused state with actions', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /^done$/i }));

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.getByText(/use your flashcards to review/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /let's practice/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /generate new set/i })).toBeInTheDocument();
    });

    it('reopens the modal when display cards is clicked from paused state', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /^done$/i }));
      await user.click(screen.getByRole('button', { name: /let's practice/i }));

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('What is React?')).toBeInTheDocument();
    });

    it('clears backend session when clear session is clicked from paused state', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );
      await openModal(user);

      await user.click(screen.getByRole('button', { name: /^done$/i }));
      await user.click(screen.getByRole('button', { name: /generate new set/i }));

      await waitFor(() => {
        expect(clearSession).toHaveBeenCalledWith({ context: defaultProps.contextData });
        expect(defaultProps.onClear).toHaveBeenCalled();
      });
    });
  });

  describe('response parsing', () => {
    it('handles response as an array of cards', async () => {
      const user = userEvent.setup();
      const cards = [makeDueCard()];
      render(
        <FlashcardStudyResponse {...defaultProps} response={cards} />,
      );

      await user.click(screen.getByRole('button', { name: /let's practice/i }));

      expect(screen.getByText('What is React?')).toBeInTheDocument();
    });

    it('handles response as an object with cards property', async () => {
      const user = userEvent.setup();
      const card = makeDueCard();
      render(
        <FlashcardStudyResponse {...defaultProps} response={{ cards: [card] }} />,
      );

      await user.click(screen.getByRole('button', { name: /let's practice/i }));

      expect(screen.getByText('What is React?')).toBeInTheDocument();
    });
  });
});
