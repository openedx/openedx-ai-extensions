import { useIntl } from '@edx/frontend-platform/i18n';
import { Button, Icon } from '@openedx/paragon';
import { ChevronLeft, ChevronRight } from '@openedx/paragon/icons';
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
    <nav aria-label={intl.formatMessage(messages['ai.library.creator.card.version.counter'], { current: selectedVersionIndex + 1, total: totalVersions })}>
      <div className="d-flex align-items-center mt-2" style={{ gap: '0.25rem' }}>
        <Button
          variant="link"
          size="sm"
          className="p-0"
          aria-label={intl.formatMessage(messages['ai.library.creator.card.version.previous'])}
          disabled={selectedVersionIndex === 0}
          onClick={onPrevious}
        >
          <Icon src={ChevronLeft} size="sm" />
        </Button>
        <span className="small" aria-current="step">
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
          <Icon src={ChevronRight} size="sm" />
        </Button>
      </div>
    </nav>
  );
};

export default VersionNavigator;
