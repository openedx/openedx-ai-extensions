import { useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Button, Container, FullscreenModal, Stepper,
} from '@openedx/paragon';
import ReviewStep from './ReviewStep';
import SaveStep from './SaveStep';
import messages from '../../messages';
import { useLibraryProblemCreatorContext } from '../../context/LibraryProblemCreatorContext';

import './EditModal.scss';

interface EditModalProps {
  displayTitle: string;
  isOpen: boolean;
  close: () => void;
}

const EditModal = ({ isOpen, close, displayTitle }: EditModalProps) => {
  const {
    selectedLibrary,
    activeCount,
    handleSave,
  } = useLibraryProblemCreatorContext();

  const intl = useIntl();
  const steps = ['review-questions', 'save-questions'];
  const [currentStep, setCurrentStep] = useState(steps[0]);
  return (
    <Stepper activeKey={currentStep}>
      <FullscreenModal
        title={displayTitle}
        className="bg-light-200"
        isOpen={isOpen}
        onClose={close}
        beforeBodyNode={<Stepper.Header className="border-bottom border-light" />}
        footerNode={(
          <>
            <Stepper.ActionRow eventKey="review-questions">
              <Stepper.ActionRow.Spacer />
              <Button onClick={() => setCurrentStep('save-questions')}>
                {intl.formatMessage(messages['ai.library.creator.modal.next'])}
              </Button>
            </Stepper.ActionRow>

            <Stepper.ActionRow eventKey="save-questions">
              <Button variant="outline-primary" onClick={() => setCurrentStep('review-questions')}>
                {intl.formatMessage(messages['ai.library.creator.modal.previous'])}
              </Button>
              <Stepper.ActionRow.Spacer />
              <Button
                variant="primary"
                disabled={!selectedLibrary || activeCount === 0}
                onClick={() => { close(); handleSave(); }}
              >
                {intl.formatMessage(messages['ai.library.creator.save.button'])}
              </Button>
            </Stepper.ActionRow>
          </>
        )}
      >
        <Container size="lg" className="py-5">
          <Stepper.Step eventKey="review-questions" title={intl.formatMessage(messages['ai.library.creator.review.step.stepper.title'])}>
            <ReviewStep />
          </Stepper.Step>

          <Stepper.Step eventKey="save-questions" title={intl.formatMessage(messages['ai.library.creator.save.step.stepper.title'])}>
            <SaveStep />
          </Stepper.Step>
        </Container>
      </FullscreenModal>
    </Stepper>
  );
};

export default EditModal;
