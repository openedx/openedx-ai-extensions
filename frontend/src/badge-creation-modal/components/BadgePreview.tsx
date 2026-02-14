/**
 * BadgePreview Component
 * Displays the generated badge and metadata
 */

import React from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Card,
  Container,
  Row,
  Col,
  Badge,
  Button,
} from '@openedx/paragon';
import { GeneratedBadge } from '../types';
import messages from '../messages';

interface BadgePreviewProps {
  badge: GeneratedBadge;
  onRefine?: () => void;
  onSave?: () => void;
  iterationCount?: number;
}

const BadgePreview: React.FC<BadgePreviewProps> = ({
  badge,
  onRefine,
  onSave,
  iterationCount = 1,
}) => {
  const intl = useIntl();

  return (
    <div className="badge-preview">
      <Container className="my-4">
        <Row className="mb-4">
          <Col xs={12} md={6}>
            <Card className="shadow-sm">
              <Card.Header title={intl.formatMessage(messages.previewTitle)} />
              <Card.Body>
                <div className="badge-preview__display">
                  <div
                    className="badge-preview__svg-container"
                    dangerouslySetInnerHTML={{ __html: badge.image }}
                    aria-label={`Generated badge: ${badge.title}`}
                  />
                  <Badge className="mt-3">
                    {intl.formatMessage(messages.iterationCount, { count: iterationCount })}
                  </Badge>
                </div>
              </Card.Body>
            </Card>
          </Col>

          <Col xs={12} md={6}>
            <Card className="shadow-sm">
              <Card.Header title="Badge Details" />
              <Card.Body>
                <div className="badge-preview__details">
                  <div className="mb-3">
                    <h6 className="text-muted">Title</h6>
                    <p>{badge.title}</p>
                  </div>

                  <div className="mb-3">
                    <h6 className="text-muted">Description</h6>
                    <p>{badge.description}</p>
                  </div>

                  {badge.metadata?.criteria && (
                    <div className="mb-3">
                      <h6 className="text-muted">Criteria</h6>
                      <p>{badge.metadata.criteria}</p>
                    </div>
                  )}

                  {badge.metadata?.skillsAligned && (
                    <div className="mb-3">
                      <h6 className="text-muted">Skills Aligned</h6>
                      <p>{badge.metadata.skillsAligned}</p>
                    </div>
                  )}

                  {badge.metadata?.awardConditions && (
                    <div className="mb-3">
                      <h6 className="text-muted">Award Conditions</h6>
                      <p>{badge.metadata.awardConditions}</p>
                    </div>
                  )}
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        <div className="badge-preview__actions d-flex gap-2 justify-content-end">
          {onRefine && (
            <Button
              variant="outline-primary"
              onClick={onRefine}
            >
              {intl.formatMessage(messages.refinButton)}
            </Button>
          )}
          {onSave && (
            <Button
              variant="primary"
              onClick={onSave}
            >
              {intl.formatMessage(messages.saveButton)}
            </Button>
          )}
        </div>
      </Container>
    </div>
  );
};

export default BadgePreview;
