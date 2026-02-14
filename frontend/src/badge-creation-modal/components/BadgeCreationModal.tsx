/**
 * BadgeCreationModal Component
 * Main modal component that wraps the badge creation workflow
 */

import { useCallback, useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  FullscreenModal,
} from '@openedx/paragon';
import { GeneratedBadge } from '../types';
import BadgeCreationWorkflow from './BadgeCreationWorkflow';
import messages from '../messages';


interface BadgeCreationModalProps {
  courseId: string;
  courseName?: string;
  isOpen: boolean;
  onClose: () => void;
  onBadgeCreated?: (badge: GeneratedBadge) => void;
}

const BadgeCreationModal = ({
  courseId,
  courseName,
  isOpen,
  onClose,
}: BadgeCreationModalProps) => {
  const intl = useIntl();
  const [error, setError] = useState<string | null>(null);

  const handleClose = useCallback(() => {
    setError(null);
    onClose();
  }, [onClose]);

  const handleError = useCallback((errorMsg: string) => {
    setError(errorMsg);
  }, []);

  const handleBadgeCreated = useCallback(
    (badge: GeneratedBadge) => {
      // Modal will close after completion based on user action
      // here needs to call the api, here we can implement 
    },
    []
  );

  return (
    <FullscreenModal
      isOpen={isOpen}
      onClose={handleClose}
      title={intl.formatMessage(messages.modalTitle)}
      className="badge-creation-modal"
    >
      {/* here we need to add the component we want to open */}
      <BadgeCreationWorkflow
        courseId={courseId}
        courseName={courseName}
        onComplete={handleBadgeCreated}
        onError={handleError}
        onClose={handleClose}
      />
    </FullscreenModal>
  );
};

export default BadgeCreationModal;
