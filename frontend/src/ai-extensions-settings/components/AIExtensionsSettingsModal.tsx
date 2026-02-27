/**
 * AIExtensionsSettingsModal Component
 *
 * Fullscreen modal with tabbed navigation for AI extensions settings.
 *
 * Tab rendering is driven by two sources:
 *  1. The built-in core Workflows tab defined in this file.
 *  2. External tabs registered at runtime via `registerComponents(REGISTRY_NAMES.SETTINGS, …)`
 *     from any plugin (e.g. openedx-ai-badges registers its badge tabs here).
 *
 * All registered tabs are always shown — no backend trip required.
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
import { getEntries, REGISTRY_NAMES, AISettingsTab } from '../../extensionRegistry';

interface AIExtensionsSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const WORKFLOWS_TAB_ID = 'workflows';

const AIExtensionsSettingsModal = ({
  isOpen,
  onClose,
}: AIExtensionsSettingsModalProps) => {
  const intl = useIntl();
  const registeredTabs = getEntries(REGISTRY_NAMES.SETTINGS) as AISettingsTab[];
  const firstTabId = registeredTabs[0]?.id ?? WORKFLOWS_TAB_ID;
  const [activeTab, setActiveTab] = useState(firstTabId);

  const workflowsCoreTab: AISettingsTab = {
    id: WORKFLOWS_TAB_ID,
    label: intl.formatMessage(messages['openedx-ai-extensions.settings-modal.tab.workflows']),
    component: WorkflowsConfigTab,
  };

  const visibleTabs: AISettingsTab[] = [...registeredTabs, workflowsCoreTab];

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
        {visibleTabs.map(({ id, label, component: TabComponent }) => (
          <Tab key={id} eventKey={id} title={label}>
            <TabComponent />
          </Tab>
        ))}
      </Tabs>
    </FullscreenModal>
  );
};

export default AIExtensionsSettingsModal;
