/**
 * AIExtensionsSettingsModal Component
 * Fullscreen modal with tabbed navigation for AI extensions settings
 */

import { useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  FullscreenModal,
  Tabs,
  Tab,
} from '@openedx/paragon';
import WorkflowsConfigTab from './WorkflowsConfigTab';
import messages from '../messages';

interface AIExtensionsSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const AIExtensionsSettingsModal = ({
  isOpen,
  onClose,
}: AIExtensionsSettingsModalProps) => {
  const intl = useIntl();
  const [activeTab, setActiveTab] = useState('workflows');

  return (
    <FullscreenModal
      isOpen={isOpen}
      onClose={onClose}
      title={intl.formatMessage(messages['openedx-ai-extensions.settings-modal.title'])}
      className="ai-extensions-settings-modal"
    >
      <Tabs
        activeKey={activeTab}
        onSelect={(key) => setActiveTab(key)}
        className="mb-3"
      >
        <Tab
          eventKey="workflows"
          title={intl.formatMessage(messages['openedx-ai-extensions.settings-modal.tab.workflows'])}
        >
          <WorkflowsConfigTab />
        </Tab>
        >
      </Tabs>
    </FullscreenModal>
  );
};

export default AIExtensionsSettingsModal;
