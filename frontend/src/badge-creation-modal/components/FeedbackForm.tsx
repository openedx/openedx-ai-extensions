/**
 * FeedbackForm Component
 * Allows users to provide feedback and feedback for badge refinement
 */

import React, { useCallback } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Form,
  Button,
  StatefulButton,
  Card,
  Alert,
} from '@openedx/paragon';
import { GeneratedBadge } from '../types';
import messages from '../messages';

interface FeedbackFormProps {
  badge: GeneratedBadge;
  onSubmit: (feedback: string) => void;
  onBack?: () => void;
  isLoading?: boolean;
  iterationCount?: number;
}

const FeedbackForm: React.FC<FeedbackFormProps> = ({
  badge,
  onSubmit,
  onBack,
  isLoading = false,
  iterationCount = 1,
}) => {
  const intl = useIntl();
  const [feedback, setFeedback] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFeedback(e.target.value);
    if (error) {
      setError(null);
    }
  }, [error]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmedFeedback = feedback.trim();

      if (!trimmedFeedback) {
        setError(intl.formatMessage(messages.requiredFieldError));
        return;
      }

      onSubmit(trimmedFeedback);
    },
    [feedback, onSubmit, intl]
  );

  return (
    <div className="feedback-form">
      <Card className="mb-4">
        <Card.Header title={intl.formatMessage(messages.feedbackTitle)} />
        <Card.Body>
          <p className="text-muted mb-4">
            {intl.formatMessage(messages.previewDescription)}
          </p>

          {error && (
            <Alert variant="danger" className="mb-3">
              {error}
            </Alert>
          )}

          <Form onSubmit={handleSubmit}>
            <Form.Group controlId="feedback-prompt">
              <Form.Label>{intl.formatMessage(messages.feedbackPromptLabel)}</Form.Label>
              <Form.Control
                as="textarea"
                placeholder={intl.formatMessage(messages.feedbackPromptPlaceholder)}
                value={feedback}
                onChange={handleChange}
                disabled={isLoading}
                maxLength={500}
                rows={4}
                aria-describedby="feedback-hint"
              />
              <Form.Text id="feedback-hint" muted className="mt-2">
                {feedback.length}/500 • {intl.formatMessage(messages.iterationCount, { count: iterationCount })}
              </Form.Text>
            </Form.Group>

            <div className="d-flex gap-2 justify-content-end mt-4">
              {onBack && (
                <Button
                  variant="outline-secondary"
                  onClick={onBack}
                  disabled={isLoading}
                >
                  {intl.formatMessage(messages.backButton)}
                </Button>
              )}
              <StatefulButton
                onClick={handleSubmit}
                disabled={isLoading || !feedback.trim()}
                state={isLoading ? 'pending' : 'default'}
                labels={{
                  default: intl.formatMessage(messages.refinButton),
                  pending: intl.formatMessage(messages.generatingMessage),
                  complete: intl.formatMessage(messages.refinButton),
                }}
              />
            </div>
          </Form>
        </Card.Body>
      </Card>

      <Alert variant="info" className="mt-3">
        <strong>Tip:</strong> Be specific with your feedback. Examples: "Make it more professional",
        "Add mathematical symbols", "Use blue and gold colors", etc.
      </Alert>
    </div>
  );
};

export default FeedbackForm;
