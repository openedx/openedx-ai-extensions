import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWrapper as render } from '../../setupTest';
import GenerateForm from './GenerateForm';

describe('GenerateForm', () => {
  describe('initial state', () => {
    it('renders with a default value of 5', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading={false} />);
      expect(screen.getByRole('spinbutton')).toHaveValue(5);
    });

    it('shows help text by default', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading={false} />);
      expect(screen.getByText(/choose between 1 and 10/i)).toBeInTheDocument();
    });

    it('renders an enabled generate button', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading={false} />);
      expect(screen.getByRole('button', { name: /generate/i })).toBeEnabled();
    });
  });

  describe('valid submission', () => {
    it('calls onGenerate with the default value on submit', async () => {
      const user = userEvent.setup();
      const onGenerate = jest.fn();
      render(<GenerateForm onGenerate={onGenerate} isLoading={false} />);

      await user.click(screen.getByRole('button', { name: /generate/i }));

      expect(onGenerate).toHaveBeenCalledTimes(1);
      expect(onGenerate).toHaveBeenCalledWith(5);
    });

    it('calls onGenerate with an updated value', async () => {
      const user = userEvent.setup();
      const onGenerate = jest.fn();
      render(<GenerateForm onGenerate={onGenerate} isLoading={false} />);

      const input = screen.getByRole('spinbutton');
      await user.clear(input);
      await user.type(input, '8');
      await user.click(screen.getByRole('button', { name: /generate/i }));

      expect(onGenerate).toHaveBeenCalledWith(8);
    });

    it('accepts the minimum boundary value of 1', async () => {
      const user = userEvent.setup();
      const onGenerate = jest.fn();
      render(<GenerateForm onGenerate={onGenerate} isLoading={false} />);

      const input = screen.getByRole('spinbutton');
      await user.clear(input);
      await user.type(input, '1');
      await user.click(screen.getByRole('button', { name: /generate/i }));

      expect(onGenerate).toHaveBeenCalledWith(1);
    });

    it('accepts the maximum boundary value of 10', async () => {
      const user = userEvent.setup();
      const onGenerate = jest.fn();
      render(<GenerateForm onGenerate={onGenerate} isLoading={false} />);

      const input = screen.getByRole('spinbutton');
      await user.clear(input);
      await user.type(input, '10');
      await user.click(screen.getByRole('button', { name: /generate/i }));

      expect(onGenerate).toHaveBeenCalledWith(10);
    });

    it('submits on Enter key', async () => {
      const user = userEvent.setup();
      const onGenerate = jest.fn();
      render(<GenerateForm onGenerate={onGenerate} isLoading={false} />);

      await user.click(screen.getByRole('spinbutton'));
      await user.keyboard('{Enter}');

      expect(onGenerate).toHaveBeenCalledWith(5);
    });
  });

  describe('validation', () => {
    it('shows a validation error when value exceeds the maximum', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading={false} />);

      fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '11' } });

      expect(screen.getByText(/must be between 1 and 10/i)).toBeInTheDocument();
      expect(screen.queryByText(/choose between 1 and 10/i)).not.toBeInTheDocument();
    });

    it('shows a validation error when value is below the minimum', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading={false} />);

      fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '0' } });

      expect(screen.getByText(/must be between 1 and 10/i)).toBeInTheDocument();
    });

    it('disables the submit button when validation fails', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading={false} />);

      fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '15' } });

      expect(screen.getByRole('button', { name: /generate/i })).toBeDisabled();
    });

    it('does not call onGenerate when validation error is present', async () => {
      const user = userEvent.setup();
      const onGenerate = jest.fn();
      render(<GenerateForm onGenerate={onGenerate} isLoading={false} />);

      const input = screen.getByRole('spinbutton');
      await user.clear(input);
      await user.type(input, '0');
      await user.click(screen.getByRole('button', { name: /generate/i }));

      expect(onGenerate).not.toHaveBeenCalled();
    });

    it('clears the validation error when user corrects the value', async () => {
      const user = userEvent.setup();
      render(<GenerateForm onGenerate={jest.fn()} isLoading={false} />);

      const input = screen.getByRole('spinbutton');
      await user.clear(input);
      await user.type(input, '15');
      expect(screen.getByText(/must be between 1 and 10/i)).toBeInTheDocument();

      await user.clear(input);
      await user.type(input, '7');
      expect(screen.queryByText(/must be between 1 and 10/i)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /generate/i })).toBeEnabled();
    });
  });

  describe('loading state', () => {
    it('disables the input while loading', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading />);
      expect(screen.getByRole('spinbutton')).toBeDisabled();
    });

    it('disables the button while loading', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading />);
      expect(screen.getByRole('button', { name: /generating/i })).toBeDisabled();
    });

    it('shows a spinner while loading', () => {
      render(<GenerateForm onGenerate={jest.fn()} isLoading />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('does not call onGenerate when loading even if form is submitted', async () => {
      const user = userEvent.setup();
      const onGenerate = jest.fn();
      render(<GenerateForm onGenerate={onGenerate} isLoading />);

      await user.keyboard('{Enter}');

      expect(onGenerate).not.toHaveBeenCalled();
    });
  });
});
