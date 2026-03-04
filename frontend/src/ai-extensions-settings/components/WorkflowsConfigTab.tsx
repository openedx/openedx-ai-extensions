/**
 * WorkflowsConfigTab Component
 * Placeholder tab for workflows configuration (to be developed)
 */

import { useIntl } from '@edx/frontend-platform/i18n';
import { Alert } from '@openedx/paragon';
import messages from '../messages';

const WorkflowsConfigTab = () => {
  const intl = useIntl();

  return (
    <div className="p-4">
      <Alert variant="info">
        {intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.placeholder'])}
      </Alert>
    </div>
  );
};

export default WorkflowsConfigTab;
