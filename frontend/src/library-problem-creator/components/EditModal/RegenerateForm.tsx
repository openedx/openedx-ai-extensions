import { useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { Button, Form, Stack } from '@openedx/paragon';
import messages from '../../messages';

interface RegenerateFormProps {
  index: number;
  onSubmit: (index: number, instructions?: string) => void;
  onCancel: () => void;
}

const RegenerateForm = ({ index, onSubmit, onCancel }: RegenerateFormProps) => {
  const intl = useIntl();
  const [instructions, setInstructions] = useState('');

  const handleSubmit = () => {
    onSubmit(index, instructions || undefined);
    setInstructions('');
  };

  const handleCancel = () => {
    setInstructions('');
    onCancel();
  };

  return (
    <div>
      <Form.Group controlId={`regen-instructions-${index}`} className="mb-1">
        <Form.Label>
          {intl.formatMessage(messages['ai.library.creator.card.regenerate.instructions.label'])}
        </Form.Label>
        <Form.Control
          as="textarea"
          rows={2}
          size="sm"
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder={intl.formatMessage(messages['ai.library.creator.card.regenerate.instructions.placeholder'])}
        />
      </Form.Group>
      <Stack direction="horizontal" gap={1}>
        <Button variant="primary" size="sm" onClick={handleSubmit}>
          {intl.formatMessage(messages['ai.library.creator.card.regenerate.confirm'])}
        </Button>
        <Button variant="outline-secondary" size="sm" onClick={handleCancel}>
          {intl.formatMessage(messages['ai.library.creator.cancel'])}
        </Button>
      </Stack>
    </div>
  );
};

export default RegenerateForm;
