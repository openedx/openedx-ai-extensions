import { useIntl } from '@edx/frontend-platform/i18n';
import { Alert } from '@openedx/paragon';
import QuestionCard from './QuestionCard';
import { useLibraryProblemCreatorContext } from '../../context/LibraryProblemCreatorContext';
import messages from '../../messages';

const ReviewStep = () => {
  const { questions, errorMessage } = useLibraryProblemCreatorContext();
  const intl = useIntl();

  return (
    <>
      <h2>{intl.formatMessage(messages['ai.library.creator.review.step.heading'])}</h2>
      <p>{intl.formatMessage(messages['ai.library.creator.review.step.description'])}</p>
      <p className="small font-weight-bold mb-2">
        {intl.formatMessage(messages['ai.library.creator.review.heading'], { count: questions.length })}
      </p>
      {errorMessage && (
        <Alert variant="danger" dismissible onClose={() => {}}>
          {errorMessage}
        </Alert>
      )}
      <div className="question-list mb-3">
        {questions.map((q, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <QuestionCard key={`${q.displayName}-${i}`} index={i} />
        ))}
      </div>
    </>
  );
};

export default ReviewStep;
