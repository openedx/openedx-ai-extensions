import React, { useState, useEffect, useMemo } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { logError } from '@edx/frontend-platform/logging';
import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import {
  Alert, Button, Card, Form, Spinner, Stack,
  useToggle,
} from '@openedx/paragon';
import { AutoAwesome } from '@openedx/paragon/icons';
import { useLibraryCreator } from '../hooks/useLibraryCreator';
import { LibraryCreatorProvider } from '../context/LibraryCreatorContext';
import messages from '../messages';
import EditModal from './EditModal';

interface LibraryComponentCreatorProps {
  courseId: string;
  locationId: string;
  uiSlotSelectorId?: string | null;
  setResponse: (response: string) => void;
  hasAsked: boolean;
  setHasAsked: (hasAsked: boolean) => void;
  titleText?: string;
  preloadPreviousSession?: boolean;
  /** Optional code-editor component (e.g. Monaco, CodeMirror) used for OLX editing */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  CodeEditor?: React.ComponentType<any> | null;
}

const LibraryComponentCreator = ({
  courseId,
  locationId,
  uiSlotSelectorId = null,
  CodeEditor = null,
  setResponse,
  hasAsked,
  setHasAsked,
  titleText,
  preloadPreviousSession = false,
}: LibraryComponentCreatorProps) => {
  const intl = useIntl();

  const displayTitle = titleText || intl.formatMessage(messages['ai.library.creator.title']);

  const questionsCreated = useLibraryCreator({
    courseId,
    locationId,
    uiSlotSelectorId,
    setResponse,
    setHasAsked,
    preloadPreviousSession,
  });

  const {
    step,
    questions,
    discardedIndices,
    errorMessage,
    generate,
    saveQuestions,
    startOver,
  } = questionsCreated;

  // Form state (idle step)
  const [showForm, setShowForm] = useState(false);
  const [numQuestions, setNumQuestions] = useState(5);
  const [extraInstructions, setExtraInstructions] = useState('');
  const [formError, setFormError] = useState('');
  const [isOpen, open, close] = useToggle(false);

  // Library picker state (review step)
  const [selectedLibrary, setSelectedLibrary] = useState('');
  const [libraries, setLibraries] = useState<Array<{ id: string; title: string }>>([]);
  const [isLoadingLibraries, setIsLoadingLibraries] = useState(false);
  const [librariesFetched, setLibrariesFetched] = useState(false);
  const [libraryError, setLibraryError] = useState('');

  const fetchLibraries = async () => {
    if (librariesFetched) { return; }
    setIsLoadingLibraries(true);
    setLibraryError('');
    try {
      const config = getConfig();
      const endpoint = `${config.STUDIO_BASE_URL}/api/libraries/v2/?pagination=false&order=title`;
      const { data } = await getAuthenticatedHttpClient().get(endpoint);
      const fetched = Array.isArray(data) ? data : (data?.results || []);
      setLibraries(fetched);
      setLibrariesFetched(true);
    } catch (err) {
      logError('LibraryComponentCreator: failed to fetch libraries:', err);
      setLibraryError(intl.formatMessage(messages['ai.library.creator.library.error']));
    } finally {
      setIsLoadingLibraries(false);
    }
  };

  // Open modal and fetch libraries when entering review step
  useEffect(() => {
    if (step === 'review') {
      open();
      fetchLibraries();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

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

  const handleSave = async () => {
    if (!selectedLibrary) {
      setLibraryError(intl.formatMessage(messages['ai.library.creator.error.no.library']));
      return;
    }
    const activeCount = questions.length - discardedIndices.size;
    if (activeCount === 0) {
      setLibraryError(intl.formatMessage(messages['ai.library.creator.error.no.questions']));
      return;
    }
    setLibraryError('');
    await saveQuestions(selectedLibrary);
  };

  const handleStartOver = async () => {
    setShowForm(false);
    setSelectedLibrary('');
    setLibraryError('');
    await startOver();
  };

  const activeCount = questions.length - discardedIndices.size;

  const contextValue = useMemo(() => ({
    ...questionsCreated,
    libraries,
    selectedLibrary,
    libraryError,
    isLoadingLibraries,
    setSelectedLibrary,
    setLibraryError,
    activeCount,
    handleSave,
    handleStartOver,
    isOpen,
    close,
    CodeEditor,
  }), [
    questionsCreated,
    libraries,
    selectedLibrary,
    libraryError,
    isLoadingLibraries,
    activeCount,
    handleSave,
    handleStartOver,
    isOpen,
    close,
    CodeEditor,
  ]);

  // Hide once hasAsked is set (response component takes over)
  // Must be AFTER all hooks to avoid "rendered fewer hooks" violation
  if (hasAsked) { return null; }

  return (
    <LibraryCreatorProvider value={contextValue}>
      <Card className="library-component-creator mt-3 mb-3">
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
                      <span className="text-danger">*</span>
                    </Form.Label>
                    <Form.Control
                      type="number"
                      min="1"
                      max="20"
                      value={numQuestions}
                      onChange={(e) => setNumQuestions(parseInt(e.target.value, 10))}
                      size="sm"
                      required
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
          {step === 'generating' && (
            <div className="text-center py-3">
              <Spinner animation="border" size="sm" className="mr-2" />
              <span className="small">
                {intl.formatMessage(messages['ai.library.creator.generating'])}
              </span>
            </div>
          )}
          {step === 'saving' && (
            <div className="text-center py-3">
              <Spinner animation="border" size="sm" className="mr-2" />
              <span className="small">
                {intl.formatMessage(messages['ai.library.creator.saving'])}
              </span>
            </div>
          )}
          <EditModal />
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
    </LibraryCreatorProvider>
  );
};

export default LibraryComponentCreator;
