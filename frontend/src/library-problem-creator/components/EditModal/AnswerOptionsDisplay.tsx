import { useIntl } from '@edx/frontend-platform/i18n';
import { Form } from '@openedx/paragon';
import { useState } from 'react';
import { Question } from '../../types';
import messages from '../../messages';

interface AnswerOptionsDisplayProps {
  question: Question;
}

const AnswerOptionsDisplay = ({ question }: AnswerOptionsDisplayProps) => {
  const intl = useIntl();
  const {
    problemType, choices, answerValue, tolerance,
  } = question;
  const [selected, setSelected] = useState('');

  // Radio buttons for single choice
  if (problemType === 'multiplechoiceresponse') {
    return (
      <Form.Group className="mt-2">
        <Form.Label className="small font-weight-bold">
          {intl.formatMessage(messages['ai.library.creator.card.field.choices'])}
        </Form.Label>
        <Form.RadioSet
          name={`answer-${question.displayName}`}
          value={choices.find((c) => c.isCorrect)?.text || ''}
        >
          {choices.map((choice) => (
            <div key={choice.text} className="mb-2">
              <Form.Radio
                value={choice.text}
                description={choice.feedback}
                isValid={choice.isCorrect}
              >
                <span>{choice.text}</span>
              </Form.Radio>
            </div>
          ))}
        </Form.RadioSet>
      </Form.Group>
    );
  }

  // Checkboxes for multiple choice
  if (problemType === 'choiceresponse') {
    return (
      <Form.Group className="mt-2">
        <Form.Label className="small font-weight-bold">
          {intl.formatMessage(messages['ai.library.creator.card.field.choices'])}
        </Form.Label>
        <Form.CheckboxSet
          name={`answer-${question.displayName}`}
          defaultValue={choices.filter((c) => c.isCorrect).map((c) => c.text)}
        >
          {choices.map((choice) => (
            <div key={choice.text} className="mb-2">
              <Form.Checkbox
                value={choice.text}
                description={choice.feedback}
                isValid={choice.isCorrect}
              >
                <p>{choice.text}</p>
              </Form.Checkbox>
            </div>
          ))}
        </Form.CheckboxSet>
      </Form.Group>
    );
  }

  // Dropdown for option response
  if (problemType === 'optionresponse') {
    return (
      <Form.Group className="mt-2">
        <Form.Label className="small font-weight-bold">
          {intl.formatMessage(messages['ai.library.creator.card.field.choices'])}
        </Form.Label>
        <Form.Control
          as="select"
          value={selected || ''}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">Select an option</option>
          {choices.map((choice) => (
            <option
              key={choice.text}
              value={choice.text}
              style={{
                color: choice.isCorrect ? 'green' : 'inherit',
                fontWeight: choice.isCorrect ? 'bold' : 'normal',
              }}
            >
              {choice.text}
            </option>
          ))}
        </Form.Control>
        <Form.Text>
          {choices.find((c) => c.text === selected)?.feedback}
        </Form.Text>
      </Form.Group>
    );
  }

  // Number input for numerical response
  if (problemType === 'numericalresponse') {
    return (
      <Form.Group className="mt-2">
        <Form.Label className="small font-weight-bold">
          {intl.formatMessage(messages['ai.library.creator.card.field.answer'])}
        </Form.Label>
        <Form.Control type="number" disabled value={answerValue || ''} />
        {tolerance && tolerance !== '<UNKNOWN>' && (
          <Form.Text className="text-muted">
            ±{tolerance} tolerance
          </Form.Text>
        )}
      </Form.Group>
    );
  }

  // Text input for string response
  if (problemType === 'stringresponse') {
    return (
      <Form.Group className="mt-2">
        <Form.Label className="small font-weight-bold">
          {intl.formatMessage(messages['ai.library.creator.card.field.answer'])}
        </Form.Label>
        <Form.Control type="text" disabled value={answerValue || ''} />
      </Form.Group>
    );
  }

  return null;
};

export default AnswerOptionsDisplay;
