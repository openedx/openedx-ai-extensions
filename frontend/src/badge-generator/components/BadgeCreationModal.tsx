/**
 * BadgeCreationModal Component
 * Main modal component that wraps the badge creation workflow
 */

import { useIntl } from '@edx/frontend-platform/i18n';
import {
  FullscreenModal,
  Container,
  Row,
  Col,
} from '@openedx/paragon';
import BadgeForm from './BadgeForm';
import messages from '../messages';


interface BadgeCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const BadgeCreationModal = ({
  isOpen,
  onClose,
}: BadgeCreationModalProps) => {
  const intl = useIntl();

  return (
    <FullscreenModal
      isOpen={isOpen}
      onClose={onClose}
      title={intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.title'])}
      className="badge-creation-modal"
    >
      <div className="badge-creation-workflow">
        <Container fluid className="h-100">
          <Row className="h-100 g-4">
            {/* Left section: Form */}
            <Col lg={6} className="d-flex flex-column">
              <div className="flex-grow-1 overflow-auto">
                <BadgeForm />
              </div>
            </Col>

            {/* Right section: Preview */}
            <Col lg={6} className="d-flex flex-column border-start align-items-center justify-content-center">
              <div className="text-center py-5 text-muted m-auto">
                <span className='display-1'>🎖️</span>
                <p className="text-center">{intl.formatMessage(messages['openedx-ai-extensions.badge-creation-modal.form.title'])}</p>
                <p className="small text-center">Your badge preview will appear here</p>
              </div>
            </Col>
          </Row>
        </Container>
      </div>
    </FullscreenModal>
  );
};

export default BadgeCreationModal;
