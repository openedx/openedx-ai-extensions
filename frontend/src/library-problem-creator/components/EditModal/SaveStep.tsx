import { useIntl } from '@edx/frontend-platform/i18n';
import { Alert, Card, Collapse, Collapsible, Container, Form, Stack } from '@openedx/paragon';
import ProblemTypeBadge from './ProblemTypeBadge';
import { useLibraryProblemCreatorContext } from '../../context/LibraryProblemCreatorContext';
import messages from '../../messages';

const SaveStep = () => {
  const {
    questions,
    discardedIndices,
    collectionName,
    setCollectionName,
    libraries,
    selectedLibrary,
    libraryError,
    isLoadingLibraries,
    setSelectedLibrary,
    setLibraryError,
  } = useLibraryProblemCreatorContext();

  const intl = useIntl();
  const activeQuestions = questions.filter((_, i) => !discardedIndices.has(i));

  return (
    <>
      <h2>{intl.formatMessage(messages['ai.library.creator.save.step.title'])}</h2>
      <p>
        {intl.formatMessage(messages['ai.library.creator.save.step.description'])}
      </p>
      <Card>
        {/* Library picker */}
        <Card.Section>
          <Form.Group controlId="librarySelect" className="mb-3">
            <Form.Label className="font-weight-bold">
              {intl.formatMessage(messages['ai.library.creator.library.label'])}
              <span className="text-danger ml-1">*</span>
            </Form.Label>
            <Form.Control
              as="select"
              value={selectedLibrary}
              onChange={(e) => { setSelectedLibrary(e.target.value); setLibraryError(''); }}
              disabled={isLoadingLibraries}
              size="sm"
            >
              <option value="">
                {isLoadingLibraries
                  ? intl.formatMessage(messages['ai.library.creator.library.loading'])
                  : intl.formatMessage(messages['ai.library.creator.library.placeholder'])}
              </option>
              {libraries.map((lib) => (
                <option key={lib.id} value={lib.id}>{`${lib.id} — ${lib.title}`}</option>
              ))}
              {!isLoadingLibraries && libraries.length === 0 && (
                <option disabled>{intl.formatMessage(messages['ai.library.creator.library.none'])}</option>
              )}
            </Form.Control>
          </Form.Group>

          {/* Collection name */}
          <Form.Group controlId="collectionName" className="mb-3">
            <Form.Label className="font-weight-bold">
              {intl.formatMessage(messages['ai.library.creator.collection.name.label'])}
            </Form.Label>
            <Form.Control
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              size="sm"
              placeholder={intl.formatMessage(messages['ai.library.creator.collection.name.placeholder'])}
            />
          </Form.Group>

          {libraryError && (
            <Alert variant="danger" className="mb-3" dismissible onClose={() => setLibraryError('')}>
              {libraryError}
            </Alert>
          )}
        </Card.Section>
        {/* Problems to be saved */}
        <Collapsible
          styling="card-lg"
          defaultOpen
          title={intl.formatMessage(messages['ai.library.creator.save.step.problems.heading'], {
            count: activeQuestions.length,
          })}>

          <Stack gap={1} className="mb-2">
            {activeQuestions.map((question, i) => (
              <div
                key={question.displayName}
                className={`d-flex align-items-center justify-content-between px-2 py-1 ${(i > activeQuestions.length -1) ?'border-bottom' :''}`}
              >
                <span className="small">{question.displayName}</span>
                <ProblemTypeBadge problemType={question.problemType} />
              </div>
            ))}
          </Stack>
        </Collapsible>
      </Card>
    </>
  );
};

export default SaveStep;
