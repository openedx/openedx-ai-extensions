import { useIntl } from '@edx/frontend-platform/i18n';
import { Button } from '@openedx/paragon';
import messages from '../../messages';

interface VersionNavigatorProps {
  selectedVersionIndex: number;
  totalVersions: number;
  onPrevious: () => void;
  onNext: () => void;
}

const VersionNavigator = ({
  selectedVersionIndex, totalVersions, onPrevious, onNext,
}: VersionNavigatorProps) => {
  const intl = useIntl();

  if (totalVersions <= 1) { return null; }

  return (
    <div className="d-flex align-items-center mt-2" style={{ gap: '0.25rem' }}>
      <Button
        variant="link"
        size="sm"
        className="p-0"
        aria-label={intl.formatMessage(messages['ai.library.creator.card.version.previous'])}
        disabled={selectedVersionIndex === 0}
        onClick={onPrevious}
      >
        ‹
      </Button>
      <span className="small text-muted">
        {intl.formatMessage(messages['ai.library.creator.card.version.counter'], {
          current: selectedVersionIndex + 1,
          total: totalVersions,
        })}
      </span>
      <Button
        variant="link"
        size="sm"
        className="p-0"
        aria-label={intl.formatMessage(messages['ai.library.creator.card.version.next'])}
        disabled={selectedVersionIndex === totalVersions - 1}
        onClick={onNext}
      >
        ›
      </Button>
    </div>
  );
};

export default VersionNavigator;
