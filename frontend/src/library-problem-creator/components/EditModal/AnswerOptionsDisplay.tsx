import { useIntl } from '@edx/frontend-platform/i18n';
import { Form } from '@openedx/paragon';
import { useState } from 'react';
import { Choice, Question } from '../../types';
import messages from '../../messages';

interface AnswerOptionsDisplayProps {
  question: Question;
}
const AnswerOptionsDisplay = ({ question }: AnswerOptionsDisplayProps) => {
  const intl = useIntl();
  const {
    problemType, choices, answerValue, tolerance,
  } = question;
  const [selected, setSelected] = useState<Choice>();

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
                className="read-only"
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
                className="read-only"
                value={choice.text}
                description={choice.feedback}
                isValid={choice.isCorrect}
              >
                {choice.text}
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
        {question.answerValue && (
        <Form.Text>
          {intl.formatMessage(messages['ai.library.creator.card.correct'], { answer: question.answerValue })}
        </Form.Text>
        )}
        <Form.Control
          as="select"
          value={selected?.text || ''}
          onChange={(e) => setSelected(choices.find(option => option.text === e.target.value))}
        >
          <option value="">
            {intl.formatMessage(messages['ai.library.creator.card.field.select.placeholder'])}
          </option>
          {choices.map((choice) => (
            <option
              key={choice.text}
              value={choice.text}
            >
              {choice.text}
            </option>
          ))}
        </Form.Control>
        {selected?.feedback && (
          <Form.Control.Feedback type={selected.isCorrect ? 'valid' : ''}>
            {selected.feedback}
          </Form.Control.Feedback>
        )}
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
        <Form.Control
          type="number"
          readOnly
          value={answerValue || ''}
          aria-label={intl.formatMessage(messages['ai.library.creator.card.field.answer'])}
        />
        {tolerance && tolerance !== '<UNKNOWN>' && (
          <Form.Text>
            {intl.formatMessage(messages['ai.library.creator.card.field.tolerance.label'], { tolerance })}
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
        <Form.Control
          as="textarea"
          autoResize
          readOnly
          value={answerValue || ''}
          aria-label={intl.formatMessage(messages['ai.library.creator.card.field.answer'])}
        />
      </Form.Group>
    );
  }

  return null;
};

export default AnswerOptionsDisplay;
