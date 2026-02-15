/**
 * BadgeCreationCard Component
 * Display card in Pages & Resources that opens the Badge Creation Modal
 * This component is injected via the AdditionalCoursePluginSlot
 */

import { useIntl } from '@edx/frontend-platform/i18n';
import { useToggle } from '@openedx/paragon';
import { CoursePagesCard } from '../components';
import { BadgeCreationModal } from './components/';
import messages from './messages';

const BadgeCreationCard = () => {
  const intl = useIntl();
  const [isModalOpen, openModal, closeModal] = useToggle(false);

  return (
    <>
      <CoursePagesCard
        title={intl.formatMessage(messages['openedx-ai-extensions.badge-creation-card.title'])}
        badge={intl.formatMessage(messages['openedx-ai-extensions.badge-creation-card.new'])}
        onClick={openModal}
        description={intl.formatMessage(messages['openedx-ai-extensions.badge-creation-card.description'])}
      />

      <BadgeCreationModal
        isOpen={isModalOpen}
        onClose={closeModal}
      />
    </>
  );
};

export default BadgeCreationCard;
