import { useState } from "react";
import { useIntl } from '@edx/frontend-platform/i18n';
import { Alert, Button, Container, Form, FullscreenModal, Stack, Stepper } from "@openedx/paragon";
import QuestionCard from './QuestionCard';
import ProblemTypeBadge from './ProblemTypeBadge';
import messages from '../messages';
import { useLibraryProblemCreatorContext } from '../context/LibraryProblemCreatorContext';

const EditModal = () => {
  const {
    questions,
    discardedIndices,
    errorMessage,
    collectionName,
    setCollectionName,
    libraries,
    selectedLibrary,
    libraryError,
    isLoadingLibraries,
    setSelectedLibrary,
    setLibraryError,
    handleSave,
    handleStartOver,
    activeCount,
    isOpen,
    close,
  } = useLibraryProblemCreatorContext();

  const activeQuestions = questions.filter((_, i) => !discardedIndices.has(i));
  const intl = useIntl();
  const steps = ['review-questions', 'save-questions'];
  const [currentStep, setCurrentStep] = useState(steps[0]);
  return (
    <>
      <Stepper activeKey={currentStep}>
        <FullscreenModal
          title={intl.formatMessage(messages['ai.library.creator.modal.title'])}
          className="bg-light-200"
          isOpen={isOpen}
          onClose={close}
          beforeBodyNode={<Stepper.Header className="border-bottom border-light" />}
          footerNode={(
            <>
              <Stepper.ActionRow eventKey="review-questions">
                <Stepper.ActionRow.Spacer />
                <Button onClick={() => setCurrentStep('save-questions')}>
                  {intl.formatMessage(messages['ai.library.creator.modal.next'])}
                </Button>
              </Stepper.ActionRow>

              <Stepper.ActionRow eventKey="save-questions">
                <Button variant="outline-primary" onClick={() => setCurrentStep('review-questions')}>
                  {intl.formatMessage(messages['ai.library.creator.modal.previous'])}
                </Button>
                <Stepper.ActionRow.Spacer />
                <Button
                  variant="primary"
                  disabled={!selectedLibrary || activeCount === 0}
                  onClick={() => { close(); handleSave(); }}
                >
                  {intl.formatMessage(messages['ai.library.creator.save.button'])}
                </Button>
              </Stepper.ActionRow>
            </>
          )}
        >
          <Container size="lg">

            <Stepper.Step eventKey="review-questions" title={intl.formatMessage(messages['ai.library.creator.review.step.stepper.title'])}>
              <h2>{intl.formatMessage(messages['ai.library.creator.review.step.heading'])}</h2>
              <p>{intl.formatMessage(messages['ai.library.creator.review.step.description'])}</p>
              <p className="small font-weight-bold mb-2">
                {intl.formatMessage(messages['ai.library.creator.review.heading'], { count: questions.length, })}
              </p>
              {errorMessage && (<Alert variant="danger" dismissible onClose={() => { }}>
                {errorMessage}
              </Alert>)
              }
              <div className="question-list mb-3">
                {questions.map((q, i) => (
                  <QuestionCard key={`${q.displayName}-${i}`} index={i} />
                ))}
              </div>
            </Stepper.Step>

            <Stepper.Step eventKey="save-questions" title={intl.formatMessage(messages['ai.library.creator.save.step.stepper.title'])}>
              <h2>{intl.formatMessage(messages['ai.library.creator.save.step.title'])}</h2>
              <p className="text-muted">
                {intl.formatMessage(messages['ai.library.creator.save.step.description'])}
              </p>

              {/* Library picker */}
              <Form.Group controlId="librarySelect" className="mb-3">
                <Form.Label className="small font-weight-bold">
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
                <Form.Label className="small font-weight-bold">
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

              {/* Problems to be saved */}
              <p className="small font-weight-bold mb-2">
                {intl.formatMessage(messages['ai.library.creator.save.step.problems.heading'], {
                  count: activeQuestions.length,
                })}
              </p>
              <Stack gap={1} className="mb-2">
                {activeQuestions.map((q) => (
                  <div
                    key={q.displayName}
                    className="d-flex align-items-center justify-content-between border rounded px-2 py-1"
                  >
                    <span className="small">{q.displayName}</span>
                    <ProblemTypeBadge problemType={q.problemType} className="ml-2" />
                  </div>
                ))}
              </Stack>
            </Stepper.Step>
          </Container>
        </FullscreenModal>
      </Stepper>
    </>
  )
}

export default EditModal;
