import RedLine from './plugin';
import GetAIAssistanceButton from './GetAIAssistanceButton';
import ConfigurableAIAssistance, {
  registerComponent,
  registerComponents,
} from './ConfigurableAIAssistance';
import { AIEducatorLibraryAssistComponent } from './components';
import { AIExtensionsCard, AIExtensionsSettingsModal } from './ai-extensions-settings';
import { REGISTRY_NAMES, getEntries } from './extensionRegistry';
import type { RegistryEntry } from './extensionRegistry';

export * as services from './services';

/*
 * Export both the configurable wrapper and the direct component.
 *
 * - ConfigurableAIAssistance: Fetches runtime config from API and renders appropriate component
 * - GetAIAssistanceButton: Direct component for advanced users who want manual control
 * - AIEducatorLibraryAssistComponent: Component for educators to generate library questions using AI
 * - registerComponent: Function to register a single workflow component from external plugins
 * - registerComponents: Function to register components or settings tabs
 *     registerComponents({ MyComponent })                              → workflow component
 *     registerComponents(REGISTRY_NAMES.SETTINGS, { id, label, component }) → settings tab
 * - REGISTRY_NAMES: Known registry name constants
 * - getEntries: Read all entries from a named registry
 * - AIExtensionsSettingsModal: Modal with tabbed settings for AI extensions (dynamic tabs)
 * - AIExtensionsCard: Card component for the Pages & Resources section (plugin slot)
 */
export {
  GetAIAssistanceButton,
  ConfigurableAIAssistance,
  RedLine,
  AIEducatorLibraryAssistComponent,
  registerComponent,
  registerComponents,
  REGISTRY_NAMES,
  getEntries,
  AIExtensionsSettingsModal,
  AIExtensionsCard,
};
export type { RegistryEntry };
