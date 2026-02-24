import RedLine from './plugin';
import GetAIAssistanceButton from './GetAIAssistanceButton';
import ConfigurableAIAssistance, {
  registerComponent,
  registerComponents,
} from './ConfigurableAIAssistance';
import { AIEducatorLibraryAssistComponent } from './components';
import { AIExtensionsCard, AIExtensionsSettingsModal } from './ai-extensions-settings';
import {
  registerAISettingsTab,
  getRegisteredAISettingsTabs,
} from './AISettingsTabRegistry';

/*
 * Export both the configurable wrapper and the direct component.
 *
 * - ConfigurableAIAssistance: Fetches runtime config from API and renders appropriate component
 * - GetAIAssistanceButton: Direct component for advanced users who want manual control
 * - AIEducatorLibraryAssistComponent: Component for educators to generate library questions using AI
 * - registerComponent: Function to register a single workflow component from external plugins
 * - registerComponents: Function to register multiple workflow components at once
 * - AIExtensionsSettingsModal: Modal with tabbed settings for AI extensions (dynamic tabs)
 * - AIExtensionsCard: Card component for the Pages & Resources section (plugin slot)
 * - registerAISettingsTab: Register a tab into the AI Extensions Settings Modal
 * - getRegisteredAISettingsTabs: Retrieve all externally registered tabs
 *
 * Plugins like openedx-ai-badges use registerComponent/registerComponents to add workflow
 * components, and registerAISettingsTab to add configuration tabs to the modal.
 */
export {
  GetAIAssistanceButton,
  ConfigurableAIAssistance,
  RedLine,
  AIEducatorLibraryAssistComponent,
  registerComponent,
  registerComponents,
  AIExtensionsSettingsModal,
  AIExtensionsCard,
  registerAISettingsTab,
  getRegisteredAISettingsTabs,
};
