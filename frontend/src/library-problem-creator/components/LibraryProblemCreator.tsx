import React, { useState, useEffect } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Button, Card, Form, Spinner, Stack, useToggle,
} from '@openedx/paragon';
import { AutoAwesome } from '@openedx/paragon/icons';
import {
  LibraryProblemCreatorProvider,
  LibraryProblemCreatorProviderProps,
  useLibraryProblemCreatorContext,
} from '../context/LibraryProblemCreatorContext';
import EditModal from './EditModal';

import messages from '../messages';

const loadingMessages = {
  generating: 'ai.library.creator.generating',
  saving: 'ai.library.creator.saving',
};

const Loading = ({ step }: { step: string }) => {
  const intl = useIntl();
  const loadingText = intl.formatMessage(messages[loadingMessages[step]]);
  return (
    <div role="status" aria-live="polite" className="text-center py-3">
      <Spinner animation="border" size="sm" className="mr-2" screenReaderText={loadingText} />
      <span className="small" aria-hidden="true">
        {loadingText}
      </span>
    </div>
  );
};

const modalSteps = new Set(['review', 'preloaded', 'saving']);

// Props are the same as the provider, minus `children`
interface LibraryProblemCreatorProps extends Omit<LibraryProblemCreatorProviderProps, 'children'> {
  hasAsked: boolean;
  titleText?: string;
}

// Inner component — has access to the context provided by the wrapper below
const LibraryProblemCreatorInner = ({
  hasAsked,
  titleText,
}: Pick<LibraryProblemCreatorProps, 'hasAsked' | 'titleText'>) => {
  const intl = useIntl();
  const {
    step,
    errorMessage,
    activeCount,
    generate,
    handleStartOver,
    fetchLibraries,
  } = useLibraryProblemCreatorContext();

  const [isOpen, open, close] = useToggle(false);

  const displayTitle = titleText || intl.formatMessage(messages['ai.library.creator.title']);
  const showReviewButton = step === 'preloaded' || (step === 'review' && !isOpen);

  // Auto-open modal only for freshly generated questions (not preloaded sessions)
  useEffect(() => {
    if (step !== 'review') { return; }
    open();
    fetchLibraries();
  }, [step, open, fetchLibraries]);

  // Form state (local to this UI — not shared with sub-components)
  const [showForm, setShowForm] = useState(false);
  const [numQuestions, setNumQuestions] = useState(5);
  const [extraInstructions, setExtraInstructions] = useState('');
  const [formError, setFormError] = useState('');

  const handleOpenModal = () => {
    open();
    fetchLibraries();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    if (numQuestions < 1 || numQuestions > 20) {
      setFormError(intl.formatMessage(messages['ai.library.creator.questions.error']));
      return;
    }
    setShowForm(false);
    await generate(numQuestions, extraInstructions || undefined);
  };

  // Hide once hasAsked is set (response component takes over)
  if (hasAsked) { return null; }

  return (
    <Card className="library-problem-creator mt-3 mb-3">
      <Card.Section>
        <h3 className="d-block mb-1">{displayTitle}</h3>
        <small className="d-block mb-2 x-small">
          {intl.formatMessage(messages['ai.library.creator.description'])}
        </small>

        {/* Idle step: show/hide form */}
        {step === 'idle' && (
          <>
            {!showForm && (
              <Button
                variant="outline-primary"
                size="sm"
                className="w-100"
                iconBefore={AutoAwesome}
                onClick={() => setShowForm(true)}
              >
                {intl.formatMessage(messages['ai.library.creator.start.button'])}
              </Button>
            )}

            {showForm && (
              <Form onSubmit={handleSubmit} className="mt-3">
                {formError && (
                  <Alert variant="danger" dismissible onClose={() => setFormError('')}>
                    {formError}
                  </Alert>
                )}
                <Form.Group controlId="numQuestions" className="mb-3">
                  <Form.Label>
                    {intl.formatMessage(messages['ai.library.creator.questions.label'])}
                    <span className="text-danger" aria-hidden="true">*</span>
                    <span className="sr-only">{intl.formatMessage(messages['ai.library.creator.field.required'])}</span>
                  </Form.Label>
                  <Form.Control
                    type="number"
                    min="1"
                    max="20"
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    size="sm"
                    required
                    aria-required="true"
                  />
                  <Form.Text>
                    <small>{intl.formatMessage(messages['ai.library.creator.questions.help'])}</small>
                  </Form.Text>
                </Form.Group>

                <Form.Group controlId="extraInstructions" className="mb-3">
                  <Form.Label>
                    {intl.formatMessage(messages['ai.library.creator.instructions.label'])}
                  </Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    value={extraInstructions}
                    onChange={(e) => setExtraInstructions(e.target.value)}
                    placeholder={intl.formatMessage(messages['ai.library.creator.instructions.placeholder'])}
                    size="sm"
                  />
                </Form.Group>

                <Stack gap={2}>
                  <Button variant="primary" type="submit" size="sm" className="w-100">
                    {intl.formatMessage(messages['ai.library.creator.generate.button'])}
                  </Button>
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    className="w-100"
                    onClick={() => { setShowForm(false); setFormError(''); }}
                  >
                    {intl.formatMessage(messages['ai.library.creator.cancel'])}
                  </Button>
                </Stack>
              </Form>
            )}
          </>
        )}

        {/* Generating step */}
        {loadingMessages[step] && <Loading step={step} />}

        {/* Questions ready but modal closed — show "Review Questions" button */}
        {showReviewButton && (
          <Stack gap={2}>
            <Button
              variant="primary"
              size="sm"
              className="w-100"
              onClick={handleOpenModal}
            >
              {intl.formatMessage(messages['ai.library.creator.review.button'], { count: activeCount })}
            </Button>
            <Button
              variant="outline-secondary"
              size="sm"
              className="w-100"
              onClick={handleStartOver}
            >
              {intl.formatMessage(messages['ai.library.creator.start.over'])}
            </Button>
          </Stack>
        )}

        {/* EditModal is always mounted when we have questions; isOpen controls visibility */}
        {modalSteps.has(step) && (
          <EditModal isOpen={isOpen} close={close} displayTitle={displayTitle} />
        )}

        {/* Error step */}
        {step === 'error' && (
          <>
            <Alert variant="danger">{errorMessage}</Alert>
            <Button
              variant="outline-secondary"
              size="sm"
              className="w-100"
              onClick={handleStartOver}
            >
              {intl.formatMessage(messages['ai.library.creator.start.over'])}
            </Button>
          </>
        )}
      </Card.Section>
    </Card>
  );
};

// Public component — sets up the provider then renders the inner UI
const LibraryProblemCreator = ({
  hasAsked,
  titleText,
  ...providerProps
}: LibraryProblemCreatorProps) => (
  <LibraryProblemCreatorProvider {...providerProps}>
    <LibraryProblemCreatorInner hasAsked={hasAsked} titleText={titleText} />
  </LibraryProblemCreatorProvider>
);

export default LibraryProblemCreator;
