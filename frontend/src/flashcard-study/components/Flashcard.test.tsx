import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWrapper as render } from '../../setupTest';
import Flashcard from './Flashcard';

const defaultProps = {
  question: 'What is the capital of France?',
  answer: 'Paris',
  isFlipped: false,
  onFlip: jest.fn(),
};

describe('Flashcard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('displays the question and allows flipping to the answer', async () => {
    const user = userEvent.setup();
    const onFlip = jest.fn();
    render(<Flashcard {...defaultProps} isFlipped={false} onFlip={onFlip} />);

    // Using exact match for the label to avoid matching "Show Question"
    expect(screen.getByText(/^question$/i)).toBeInTheDocument();
    expect(screen.getByText(defaultProps.question)).toBeInTheDocument();

    // Find and click the button to show the answer
    const showAnswerBtn = screen.getByRole('button', { name: /show answer/i });
    await user.click(showAnswerBtn);

    expect(onFlip).toHaveBeenCalledTimes(1);
  });

  it('displays the answer and allows flipping back to the question', async () => {
    const user = userEvent.setup();
    const onFlip = jest.fn();
    render(<Flashcard {...defaultProps} isFlipped onFlip={onFlip} />);

    // Using exact match for the label to avoid matching "Show Answer"
    expect(screen.getByText(/^answer$/i)).toBeInTheDocument();
    expect(screen.getByText(defaultProps.answer)).toBeInTheDocument();

    // Find and click the button to show the question
    const showQuestionBtn = screen.getByRole('button', { name: /show question/i });
    await user.click(showQuestionBtn);

    expect(onFlip).toHaveBeenCalledTimes(1);
  });

  it('marks the front face as inert when flipped', () => {
    const { container } = render(<Flashcard {...defaultProps} isFlipped />);
    const front = container.querySelector('.flashcard-face--front');
    expect(front).toHaveAttribute('inert');
  });

  it('marks the back face as inert when not flipped', () => {
    const { container } = render(<Flashcard {...defaultProps} isFlipped={false} />);
    const back = container.querySelector('.flashcard-face--back');
    expect(back).toHaveAttribute('inert');
  });
});
