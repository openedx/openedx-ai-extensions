import { useIntl } from '@edx/frontend-platform/i18n';
import { Badge } from '@openedx/paragon';
import messages from '../../messages';

interface ProblemTypeBadgeProps {
  problemType: string;
  className?: string;
}

const PROBLEM_TYPE_MESSAGE_IDS: Record<string, string> = {
  multiplechoiceresponse: 'ai.library.creator.problemtype.multiplechoiceresponse',
  choiceresponse: 'ai.library.creator.problemtype.choiceresponse',
  optionresponse: 'ai.library.creator.problemtype.optionresponse',
  numericalresponse: 'ai.library.creator.problemtype.numericalresponse',
  stringresponse: 'ai.library.creator.problemtype.stringresponse',
};

const ProblemTypeBadge = ({ problemType, className }: ProblemTypeBadgeProps) => {
  const intl = useIntl();
  const messageId = PROBLEM_TYPE_MESSAGE_IDS[problemType];
  const label = messageId
    ? intl.formatMessage(messages[messageId as keyof typeof messages])
    : problemType;

  return (
    <Badge pill variant="info" className={className ?? ''}>
      {label}
    </Badge>
  );
};

export default ProblemTypeBadge;
