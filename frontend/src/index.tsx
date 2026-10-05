import RedLine from './plugin';
import GetAIAssistanceButton from './GetAIAssistanceButton';
import ConfigurableAIAssistance, {
  registerComponent,
  registerComponents,
} from './ConfigurableAIAssistance';
import { AIExtensionsCard, AIExtensionsSettingsModal } from './ai-extensions-settings';
import AIUnitSidebarPanel, { DEFAULT_UNIT_SIDEBAR_BOXES } from './AIUnitSidebarPanel';
import type { AISidebarBox } from './AIUnitSidebarPanel';
import { REGISTRY_NAMES, getEntries } from './extensionRegistry';
import type { RegistryEntry } from './extensionRegistry';
import {
  LibraryProblemCreator,
  LibraryProblemCreatorResponse,
} from './library-problem-creator';
import FlashcardCreator from './flashcard-study/components/FlashcardCreator';
import FlashcardStudyResponse from './flashcard-study/components/FlashcardStudyResponse';

export * as services from './services';

/*
 * Export both the configurable wrapper and the direct component.
 *
 * - ConfigurableAIAssistance: Fetches runtime config from API and renders appropriate component
 * - GetAIAssistanceButton: Direct component for advanced users who want manual control
 * - registerComponent: Function to register a single workflow component from external plugins
 * - registerComponents: Function to register components or settings tabs
 *     registerComponents({ MyComponent })                              → workflow component
 *     registerComponents(REGISTRY_NAMES.SETTINGS, { id, label, component }) → settings tab
 * - REGISTRY_NAMES: Known registry name constants
 * - getEntries: Read all entries from a named registry
 * - AIExtensionsSettingsModal: Modal with tabbed settings for AI extensions (dynamic tabs)
 * - AIExtensionsCard: Card component for the Pages & Resources section (plugin slot)
 * - AIUnitSidebarPanel: Wraps Studio's unit sidebar to add an AI page to it
 */
export {
  GetAIAssistanceButton,
  ConfigurableAIAssistance,
  RedLine,
  LibraryProblemCreator,
  LibraryProblemCreatorResponse,
  registerComponent,
  registerComponents,
  REGISTRY_NAMES,
  getEntries,
  AIExtensionsSettingsModal,
  AIExtensionsCard,
  FlashcardCreator,
  FlashcardStudyResponse,
  AIUnitSidebarPanel,
  DEFAULT_UNIT_SIDEBAR_BOXES,
};
export type { RegistryEntry, AISidebarBox };
