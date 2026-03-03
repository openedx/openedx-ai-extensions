/**
 * AIExtensionsCard Component
 * Display card in Pages & Resources that opens the AI Extensions Settings Modal
 * This component is injected via the AdditionalCoursePluginSlot
 */

import { useIntl } from '@edx/frontend-platform/i18n';
import { useToggle } from '@openedx/paragon';
import { CoursePagesCard } from '../components';
import { AIExtensionsSettingsModal } from './components';
import messages from './messages';

interface AIExtensionsCardProps {
  id?: string | null;
  [key: string]: any;
}

const AIExtensionsCard = ({ id = null }: AIExtensionsCardProps) => {
  const intl = useIntl();
  const [isModalOpen, openModal, closeModal] = useToggle(false);

  return (
    <>
      <CoursePagesCard
        title={intl.formatMessage(messages['openedx-ai-extensions.settings-card.title'])}
        badge={intl.formatMessage(messages['openedx-ai-extensions.settings-card.badge'])}
        onClick={openModal}
        description={intl.formatMessage(messages['openedx-ai-extensions.settings-card.description'])}
      />

      <AIExtensionsSettingsModal
        isOpen={isModalOpen}
        onClose={closeModal}
        uiSlotSelectorId={id}
      />
    </>
  );
};

export default AIExtensionsCard;
