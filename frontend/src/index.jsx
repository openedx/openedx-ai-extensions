import RedLine from './plugin';
import GetAIAssistanceButton from './GetAIAssistanceButton';
import ConfigurableAIAssistance, {
  registerComponent,
  registerComponents,
} from './ConfigurableAIAssistance';
import { AIEducatorLibraryAssistComponent } from './components';

/*
 * Export both the configurable wrapper and the direct component.
 *
 * - ConfigurableAIAssistance: Fetches runtime config from API and renders appropriate component
 * - GetAIAssistanceButton: Direct component for advanced users who want manual control
 * - AIEducatorLibraryAssistComponent: Component for educators to generate library questions using AI
 * - registerComponent: Function to register a single component from external plugins
 * - registerComponents: Function to register multiple components at once
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
};
