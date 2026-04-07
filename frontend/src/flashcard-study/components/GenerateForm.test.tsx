import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWrapper as render } from '../../setupTest';
import GenerateForm from './GenerateForm';

const defaultProps = {
  onGenerate: jest.fn(),
  isLoading: false,
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('GenerateForm', () => {
  describe('initial state', () => {
    it('shows instructional text', () => {
      render(<GenerateForm {...defaultProps} />);
      expect(screen.getByText(/choose a study depth or let ai decide/i)).toBeInTheDocument();
    });

    it('renders four depth options', () => {
      render(<GenerateForm {...defaultProps} />);
      expect(screen.getByText('Auto')).toBeInTheDocument();
      expect(screen.getByText('5 cards')).toBeInTheDocument();
      expect(screen.getByText('15 cards')).toBeInTheDocument();
      expect(screen.getByText('25 cards')).toBeInTheDocument();
    });

    it('shows sublabels for each option', () => {
      render(<GenerateForm {...defaultProps} />);
      expect(screen.getByText('Optimal')).toBeInTheDocument();
      expect(screen.getByText('Quick')).toBeInTheDocument();
      expect(screen.getByText('Standard')).toBeInTheDocument();
      expect(screen.getByText('Deep')).toBeInTheDocument();
    });
  });

  describe('depth selection', () => {
    it('calls onGenerate with null when Auto is clicked', async () => {
      const user = userEvent.setup();
      render(<GenerateForm {...defaultProps} />);

      await user.click(screen.getByText('Auto'));

      expect(defaultProps.onGenerate).toHaveBeenCalledWith(null);
    });

    it('calls onGenerate with 5 when Quick is clicked', async () => {
      const user = userEvent.setup();
      render(<GenerateForm {...defaultProps} />);

      await user.click(screen.getByText('5 cards'));

      expect(defaultProps.onGenerate).toHaveBeenCalledWith(5);
    });

    it('calls onGenerate with 15 when Standard is clicked', async () => {
      const user = userEvent.setup();
      render(<GenerateForm {...defaultProps} />);

      await user.click(screen.getByText('15 cards'));

      expect(defaultProps.onGenerate).toHaveBeenCalledWith(15);
    });

    it('calls onGenerate with 25 when Deep is clicked', async () => {
      const user = userEvent.setup();
      render(<GenerateForm {...defaultProps} />);

      await user.click(screen.getByText('25 cards'));

      expect(defaultProps.onGenerate).toHaveBeenCalledWith(25);
    });
  });

  describe('loading state', () => {
    it('disables all depth options while loading', () => {
      render(<GenerateForm {...defaultProps} isLoading />);
      const buttons = screen.getAllByRole('button');
      buttons.forEach((btn) => {
        expect(btn).toBeDisabled();
      });
    });
  });
});
