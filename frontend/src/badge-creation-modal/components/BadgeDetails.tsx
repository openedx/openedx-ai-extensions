/**
 * BadgeDetails Component
 * Displays badge information with collapsible feedback form
 */

import React, { useState, useCallback } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Card,
  Button,
  Collapsible,
  Form,
  StatefulButton,
} from '@openedx/paragon';
import { GeneratedBadge } from '../types';
import messages from '../messages';

interface BadgeDetailsProps {
  badge: GeneratedBadge;
  iterationCount: number;
  isLoading?: boolean;
  onRefine: (feedback: string) => void;
  onSave: () => void;
}

const BadgeDetails: React.FC<BadgeDetailsProps> = ({
  badge,
  iterationCount,
  isLoading = false,
  onRefine,
  onSave,
}) => {
  const intl = useIntl();
  const [feedback, setFeedback] = useState('');
  const [isRefineOpen, setIsRefineOpen] = useState(false);

  const handleFeedbackSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (feedback.trim()) {
        onRefine(feedback);
        setFeedback('');
        setIsRefineOpen(false);
      }
    },
    [feedback, onRefine]
  );

  return (
    <div className="badge-details">
      {/* Badge Metadata */}
      <Card className="mb-4">
        <Card.Header 
          title="Badge Details"
          subtitle={`Iteration ${iterationCount}`}
        />
        <Card.Body>
          <div className="mb-3">
            <h6 className="text-muted mb-2">Title</h6>
            <p className="mb-0">{badge.title}</p>
          </div>

          <div className="mb-3">
            <h6 className="text-muted mb-2">Description</h6>
            <p className="mb-0">{badge.description}</p>
          </div>

          {badge.metadata?.scope && (
            <div className="mb-3">
              <h6 className="text-muted mb-2">Scope</h6>
              <p className="mb-0 text-capitalize">{badge.metadata.scope}</p>
            </div>
          )}

          {badge.metadata?.style && (
            <div className="mb-3">
              <h6 className="text-muted mb-2">Style</h6>
              <p className="mb-0 text-capitalize">{badge.metadata.style}</p>
            </div>
          )}

          {badge.metadata?.tone && (
            <div className="mb-3">
              <h6 className="text-muted mb-2">Tone</h6>
              <p className="mb-0 text-capitalize">{badge.metadata.tone}</p>
            </div>
          )}

          {badge.metadata?.level && (
            <div className="mb-3">
              <h6 className="text-muted mb-2">Level</h6>
              <p className="mb-0 text-capitalize">{badge.metadata.level}</p>
            </div>
          )}

          {badge.metadata?.criterion && (
            <div className="mb-3">
              <h6 className="text-muted mb-2">Criterion</h6>
              <p className="mb-0 text-capitalize">{badge.metadata.criterion}</p>
            </div>
          )}

          {badge.metadata?.skillsEnabled && (
            <div className="mb-3">
              <h6 className="text-muted mb-2">Skills Extraction</h6>
              <p className="mb-0">
                <span className="badge bg-success">Enabled</span>
              </p>
            </div>
          )}

          {badge.metadata?.userDescription && (
            <div className="mb-3">
              <h6 className="text-muted mb-2">User Description</h6>
              <p className="mb-0 text-muted small">{badge.metadata.userDescription}</p>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Collapsible Refine Form */}
      <Collapsible
        title="Refine Badge"
        className="mb-4"
        open={isRefineOpen}
        onToggle={setIsRefineOpen}
      >
        <Card>
          <Card.Body>
            <Form onSubmit={handleFeedbackSubmit}>
              <Form.Group className="mb-3">
                <Form.Label>
                  {intl.formatMessage(messages.feedbackPromptLabel)}
                </Form.Label>
                <Form.Control
                  as="textarea"
                  rows={4}
                  placeholder={intl.formatMessage(messages.feedbackPromptPlaceholder)}
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  disabled={isLoading}
                />
                <Form.Text muted className="mt-2">
                  {feedback.length}/500
                </Form.Text>
              </Form.Group>

              <div className="d-flex gap-2">
                <StatefulButton
                  type="submit"
                  disabled={isLoading || !feedback.trim()}
                  state={isLoading ? 'pending' : 'default'}
                  labels={{
                    default: intl.formatMessage(messages.refinButton),
                    pending: intl.formatMessage(messages.generatingMessage),
                    complete: intl.formatMessage(messages.refinButton),
                  }}
                />
                <Button
                  variant="outline-secondary"
                  onClick={() => setIsRefineOpen(false)}
                  disabled={isLoading}
                >
                  {intl.formatMessage(messages.cancelButton)}
                </Button>
              </div>
            </Form>
          </Card.Body>
        </Card>
      </Collapsible>

      {/* Action Buttons */}
      <div className="badge-details__actions d-flex gap-2 flex-direction-column">
        <Button
          variant="primary"
          onClick={onSave}
          disabled={isLoading}
          className="flex-grow-1"
        >
          {intl.formatMessage(messages.saveButton)}
        </Button>
        <Button
          variant="outline-primary"
          onClick={() => setIsRefineOpen(!isRefineOpen)}
          disabled={isLoading}
          className="flex-grow-1"
        >
          {isRefineOpen ? 'Cancel' : intl.formatMessage(messages.refinButton)}
        </Button>
      </div>
    </div>
  );
};

export default BadgeDetails;
