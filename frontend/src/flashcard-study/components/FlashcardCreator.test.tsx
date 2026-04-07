import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWrapper as render } from '../../setupTest';
import FlashcardCreator from './FlashcardCreator';
import { generateFlashcards, getSessionResponse } from '../data/workflowActions';
import { useAsyncTaskPolling } from '../hooks/useAsyncTaskPolling';

jest.mock('../data/workflowActions', () => ({
  generateFlashcards: jest.fn(),
  getSessionResponse: jest.fn(),
}));

jest.mock('../hooks/useAsyncTaskPolling', () => ({
  POLLING_ERROR_KEYS: { TIMEOUT: 'timeout', GENERATE: 'generate', NETWORK: 'network' },
  useAsyncTaskPolling: jest.fn(),
}));

const mockStartPolling = jest.fn();
const mockStopPolling = jest.fn();

const defaultProps = {
  hasAsked: false,
  setResponse: jest.fn(),
  setHasAsked: jest.fn(),
  courseId: 'course-v1:Test+101+2024',
  locationId: 'block-v1:Test+101+2024+type@vertical+block@abc',
  uiSlotSelectorId: 'openedx.learning.unit.header.slot.v1',
};

beforeEach(() => {
  jest.clearAllMocks();
  (useAsyncTaskPolling as jest.Mock).mockReturnValue({
    startPolling: mockStartPolling,
    stopPolling: mockStopPolling,
  });
});

const clickCreateButton = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(screen.getByRole('button', { name: /create new cards/i }));
};

const clickAutoDepth = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(screen.getByRole('button', { name: /auto/i }));
};

const generateWithAuto = async (user: ReturnType<typeof userEvent.setup>) => {
  await clickCreateButton(user);
  await clickAutoDepth(user);
};

describe('FlashcardCreator', () => {
  describe('when preloadPreviousSession is enabled', () => {
    it('shows a loading state while checking', () => {
      (getSessionResponse as jest.Mock).mockReturnValue(new Promise(() => {}));
      render(<FlashcardCreator {...defaultProps} preloadPreviousSession />);

      const btn = screen.getByRole('button', { name: /loading/i });
      expect(btn).toBeInTheDocument();
      expect(btn).toHaveAttribute('aria-disabled', 'true');
    });

    it('hands off to the response component when a session with cards exists', async () => {
      const sessionData = {
        status: 'completed',
        cards: [{ id: '1', question: 'Q1' }],
      };
      (getSessionResponse as jest.Mock).mockResolvedValue(sessionData);
      render(<FlashcardCreator {...defaultProps} preloadPreviousSession />);

      await waitFor(() => {
        expect(defaultProps.setResponse).toHaveBeenCalledWith({ ...sessionData, fromSession: true });
        expect(defaultProps.setHasAsked).toHaveBeenCalledWith(true);
      });
    });

    it('shows the create button when no session exists', async () => {
      (getSessionResponse as jest.Mock).mockResolvedValue({ cards: [] });
      render(<FlashcardCreator {...defaultProps} preloadPreviousSession />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create new cards/i })).toBeInTheDocument();
      });
    });

    it('shows the create button when the session check fails', async () => {
      (getSessionResponse as jest.Mock).mockRejectedValue(new Error('Network'));
      render(<FlashcardCreator {...defaultProps} preloadPreviousSession />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create new cards/i })).toBeInTheDocument();
      });
    });

    it('does not call getSessionResponse when preloadPreviousSession is false', () => {
      render(<FlashcardCreator {...defaultProps} />);

      expect(getSessionResponse).not.toHaveBeenCalled();
      expect(screen.getByRole('button', { name: /create new cards/i })).toBeInTheDocument();
    });
  });

  describe('when the user sees the initial screen', () => {
    it('shows the description and create button immediately', () => {
      render(<FlashcardCreator {...defaultProps} />);

      expect(screen.getByText(/generate flashcards from the course content/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create new cards/i })).toBeInTheDocument();
    });

    it('shows the generate form when the create button is clicked', async () => {
      const user = userEvent.setup();
      render(<FlashcardCreator {...defaultProps} />);

      await clickCreateButton(user);

      expect(screen.getByText(/choose a study depth/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /auto/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^5 cards/i })).toBeInTheDocument();
    });

    it('hides the component when the response is already shown', () => {
      const { container } = render(<FlashcardCreator {...defaultProps} hasAsked />);
      expect(container).toBeEmptyDOMElement();
    });
  });

  describe('when the user creates new flashcards', () => {
    it('shows generating state after clicking a depth option', async () => {
      const user = userEvent.setup();
      (generateFlashcards as jest.Mock).mockReturnValue(new Promise(() => {}));
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      const btn = screen.getByRole('button');
      expect(btn).toHaveAttribute('aria-disabled', 'true');
    });

    it('calls generateFlashcards with null numCards for auto depth', async () => {
      const user = userEvent.setup();
      (generateFlashcards as jest.Mock).mockResolvedValue({ taskId: 'task-1' });
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      await waitFor(() => {
        expect(generateFlashcards).toHaveBeenCalledWith(
          expect.objectContaining({ numCards: null }),
        );
      });
    });

    it('calls generateFlashcards with specific numCards for a depth option', async () => {
      const user = userEvent.setup();
      (generateFlashcards as jest.Mock).mockResolvedValue({ taskId: 'task-1' });
      render(<FlashcardCreator {...defaultProps} />);

      await clickCreateButton(user);
      await user.click(screen.getByRole('button', { name: /^5 cards/i }));

      await waitFor(() => {
        expect(generateFlashcards).toHaveBeenCalledWith(
          expect.objectContaining({ numCards: 5 }),
        );
      });
    });

    it('starts polling when the backend returns a task ID', async () => {
      const user = userEvent.setup();
      (generateFlashcards as jest.Mock).mockResolvedValue({ taskId: 'task-123' });
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      await waitFor(() => {
        expect(mockStartPolling).toHaveBeenCalledWith('task-123');
      });
    });

    it('sets the response directly when the backend returns data without a task ID', async () => {
      const user = userEvent.setup();
      const responseData = { cards: [{ id: '1' }] };
      (generateFlashcards as jest.Mock).mockResolvedValue(responseData);
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      await waitFor(() => {
        expect(defaultProps.setResponse).toHaveBeenCalledWith(responseData);
        expect(defaultProps.setHasAsked).toHaveBeenCalledWith(true);
      });
    });

    it('shows an error message when the API call fails', async () => {
      const user = userEvent.setup();
      (generateFlashcards as jest.Mock).mockRejectedValue(new Error('Server error'));
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      await waitFor(() => {
        expect(screen.getByText(/failed to generate flashcards/i)).toBeInTheDocument();
      });
    });

    it('displays backend progress message during polling', async () => {
      let capturedOnProgress: (msg: string) => void;
      (useAsyncTaskPolling as jest.Mock).mockImplementation((opts: any) => {
        capturedOnProgress = opts.onProgress;
        return { startPolling: mockStartPolling, stopPolling: mockStopPolling };
      });
      (generateFlashcards as jest.Mock).mockResolvedValue({ taskId: 'task-456', message: 'Reading unit...' });
      const user = userEvent.setup();
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      await waitFor(() => {
        expect(screen.getByText('Reading unit...')).toBeInTheDocument();
      });

      capturedOnProgress!('Building cards...');

      await waitFor(() => {
        expect(screen.getByText('Building cards...')).toBeInTheDocument();
      });
    });
  });

  describe('when the user encounters an error', () => {
    it('can return to the initial screen by dismissing the error', async () => {
      const user = userEvent.setup();
      (generateFlashcards as jest.Mock).mockRejectedValue(new Error('fail'));
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /dismiss/i }));

      expect(screen.getByRole('button', { name: /create new cards/i })).toBeInTheDocument();
      expect(screen.queryByText(/failed to generate/i)).not.toBeInTheDocument();
    });

    it('stops polling when dismissed', async () => {
      const user = userEvent.setup();
      (generateFlashcards as jest.Mock).mockRejectedValue(new Error('fail'));
      render(<FlashcardCreator {...defaultProps} />);

      await generateWithAuto(user);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /dismiss/i }));
      expect(mockStopPolling).toHaveBeenCalled();
    });

    it('shows a timeout message when polling times out', () => {
      render(<FlashcardCreator {...defaultProps} />);

      const { onError } = (useAsyncTaskPolling as jest.Mock).mock.calls[0][0];
      act(() => { onError('timeout'); });

      expect(screen.getByText(/generation timed out/i)).toBeInTheDocument();
    });

    it('shows a network error message on connectivity issues', () => {
      render(<FlashcardCreator {...defaultProps} />);

      const { onError } = (useAsyncTaskPolling as jest.Mock).mock.calls[0][0];
      act(() => { onError('network'); });

      expect(screen.getByText(/network error occurred/i)).toBeInTheDocument();
    });
  });
});
