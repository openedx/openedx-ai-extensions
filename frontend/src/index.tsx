import RedLine from './plugin';
import GetAIAssistanceButton from './GetAIAssistanceButton';
import ConfigurableAIAssistance from './ConfigurableAIAssistance';
import { AIEducatorLibraryAssistComponent } from './components';
import { BadgeCreationCard, BadgeCreationModal } from './badge-creation-modal';

/*
 * Export both the configurable wrapper and the direct component.
 *
 * - ConfigurableAIAssistance: Fetches runtime config from API and renders appropriate component
 * - GetAIAssistanceButton: Direct component for advanced users who want manual control
 * - AIEducatorLibraryAssistComponent: Component for educators to generate library questions using AI
 * - BadgeCreationModal: Modal for AI-driven badge creation with human-in-the-loop workflow
 * - BadgeCreationCard: Card component for the Pages & Resources section (plugin slot)
 *
 * If we want to add more plugins, we would import them above and then add them to the list of exports below.
 */
export {
  GetAIAssistanceButton,
  ConfigurableAIAssistance,
  RedLine,
  AIEducatorLibraryAssistComponent,
  BadgeCreationModal,
  BadgeCreationCard,
};
