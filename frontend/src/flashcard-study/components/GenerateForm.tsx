import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Button, ButtonGroup, Container, Icon,
} from '@openedx/paragon';
import { AutoAwesome } from '@openedx/paragon/icons';
import messages from '../messages';

interface DepthOption {
  value: string;
  numCards: number | null;
  sublabelKey: keyof typeof messages;
  icon?: typeof Icon;
}

const DEPTH_OPTIONS: DepthOption[] = [
  {
    value: 'auto', numCards: null, sublabelKey: 'ai.extensions.flashcard.generate.depth.auto.sublabel', icon: AutoAwesome,
  },
  { value: '5', numCards: 5, sublabelKey: 'ai.extensions.flashcard.generate.depth.quick' },
  { value: '15', numCards: 15, sublabelKey: 'ai.extensions.flashcard.generate.depth.standard' },
  { value: '25', numCards: 25, sublabelKey: 'ai.extensions.flashcard.generate.depth.deep' },
];

export interface GenerateFormProps {
  onGenerate: (numCards: number | null) => void;
  isLoading: boolean;
}

const GenerateForm = ({ onGenerate, isLoading }: GenerateFormProps) => {
  const intl = useIntl();

  return (

    <Container className="d-flex align-items-center justify-content-end px-3 small flex-wrap">
      <span className="d-block my-2 pr-md-5 container-mw-xs">{intl.formatMessage(messages['ai.extensions.flashcard.generate.form.auto.help'])}</span>
      <ButtonGroup size="sm" className="w-sm-100 w-md-25">
        {DEPTH_OPTIONS.map(({
          value, numCards, sublabelKey, icon,
        }) => (
          <Button
            key={value}
            iconBefore={icon}
            variant="outline-primary"
            onClick={() => onGenerate(numCards)}
            disabled={isLoading}
          >
            <div className="d-flex flex-column x-small">

              <strong>
                {numCards === null
                  ? intl.formatMessage(messages['ai.extensions.flashcard.generate.depth.auto'])
                  : intl.formatMessage(messages['ai.extensions.flashcard.generate.depth.cards'], { count: numCards })}
              </strong>
              <span>{intl.formatMessage(messages[sublabelKey])}</span>
            </div>
          </Button>
        ))}
      </ButtonGroup>
    </Container>
  );
};

export default GenerateForm;
