import RedLine from './plugin';
import GetAIAssistanceButton from './GetAIAssistanceButton';
import ConfigurableAIAssistance, {
  registerComponent,
  registerComponents,
} from './ConfigurableAIAssistance';
import { AIEducatorLibraryAssistComponent } from './components';
import { AIExtensionsCard, AIExtensionsSettingsModal } from './ai-extensions-settings';

/*
 * Export both the configurable wrapper and the direct component.
 *
 * - ConfigurableAIAssistance: Fetches runtime config from API and renders appropriate component
 * - GetAIAssistanceButton: Direct component for advanced users who want manual control
 * - AIEducatorLibraryAssistComponent: Component for educators to generate library questions using AI
 * - registerComponent: Function to register a single component from external plugins
 * - registerComponents: Function to register multiple components at once
 * - AIExtensionsSettingsModal: Modal with tabbed settings for AI extensions (badges, workflows, etc.)
 * - AIExtensionsCard: Card component for the Pages & Resources section (plugin slot)
 *
 * Plugins like ai-badges can use registerComponent/registerComponents to add their own components
 * to the internal component registry, making them available for use with ConfigurableAIAssistance.
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
};
