import { useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Button, Form, Spinner } from '@openedx/paragon';
import messages from '../messages';

const MIN_CARDS = 1;
const MAX_CARDS = 10;
const DEFAULT_CARDS = 5;

export interface GenerateFormProps {
  onGenerate: (numCards: number) => void;
  isLoading: boolean;
}

const GenerateForm = ({ onGenerate, isLoading }: GenerateFormProps) => {
  const intl = useIntl();
  const [numCards, setNumCards] = useState(DEFAULT_CARDS);
  const [validationError, setValidationError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    setNumCards(value);
    if (Number.isNaN(value) || value < MIN_CARDS || value > MAX_CARDS) {
      setValidationError(intl.formatMessage(messages['ai.extensions.flashcard.generate.form.error']));
    } else {
      setValidationError('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validationError || isLoading) { return; }
    onGenerate(numCards);
  };

  const isInvalid = !!validationError;

  return (
    <Form onSubmit={handleSubmit}>
      <Form.Group controlId="flashcard-num-cards" isInvalid={isInvalid}>
        <Form.Label>
          {intl.formatMessage(messages['ai.extensions.flashcard.generate.form.label'])}
        </Form.Label>
        <Form.Control
          type="number"
          value={numCards}
          min={MIN_CARDS}
          max={MAX_CARDS}
          onChange={handleChange}
          disabled={isLoading}
        />
        {isInvalid ? (
          <Form.Control.Feedback type="invalid">
            {validationError}
          </Form.Control.Feedback>
        ) : (
          <Form.Text>
            {intl.formatMessage(messages['ai.extensions.flashcard.generate.form.help'])}
          </Form.Text>
        )}
      </Form.Group>
      <Button
        type="submit"
        variant="primary"
        disabled={isInvalid || isLoading}
        className="mt-2"
      >
        {isLoading ? (
          <>
            <Spinner animation="border" size="sm" className="mr-2" screenReaderText="loading" />
            {intl.formatMessage(messages['ai.extensions.flashcard.generate.form.generating'])}
          </>
        ) : (
          intl.formatMessage(messages['ai.extensions.flashcard.generate.form.submit'])
        )}
      </Button>
    </Form>
  );
};

export default GenerateForm;
