import React, { useState, useEffect, useRef } from 'react';
import { logError, logInfo } from '@edx/frontend-platform/logging';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Button,
  Form,
  Spinner,
  Alert,
  Card,
  Stack,
} from '@openedx/paragon';
import { AutoAwesome, Close } from '@openedx/paragon/icons';
import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import { callWorkflowService, prepareContextData } from '../services';
import { WORKFLOW_ACTIONS } from '../constants';
import messages from '../messages';

interface AIEducatorLibraryAssistComponentProps {
  courseId: string;
  locationId: string;
  setResponse: (response: string) => void;
  hasAsked: boolean;
  setHasAsked: (hasAsked: boolean) => void;
  libraries?: Array<{ id: string; title: string }>;
  titleText?: string;
  buttonText?: string;
  preloadPreviousSession?: boolean;
  customMessage?: string;
  onSuccess?: () => void;
  onError?: (error: any) => void;
  debug?: boolean;
}

/**
 * AI Educator Library Assist Component
 * Allows educators to generate questions for the current unit using AI
 * and add them to a selected library
 */
const AIEducatorLibraryAssistComponent = ({
  courseId,
  locationId,
  setResponse,
  hasAsked,
  setHasAsked,
  libraries: librariesProp,
  titleText,
  buttonText,
  customMessage,
  preloadPreviousSession = false,
  onSuccess,
  onError,
  debug = false,
}: AIEducatorLibraryAssistComponentProps) => {
  const intl = useIntl();
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Default display values
  const displayTitle = titleText || intl.formatMessage(messages['ai.extensions.educator.title']);
  const displayButtonText = buttonText || intl.formatMessage(messages['ai.extensions.educator.start']);
  const displayCustomMessage = customMessage || intl.formatMessage(messages['ai.extensions.educator.default.message']);

  // Libraries state
  const [libraries, setLibraries] = useState(librariesProp || []);
  const [isLoadingLibraries, setIsLoadingLibraries] = useState(false);
  const [librariesFetched, setLibrariesFetched] = useState(false);

  // Form state
  const [selectedLibrary, setSelectedLibrary] = useState('');
  const [numberOfQuestions, setNumberOfQuestions] = useState(5);
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  // Track if we've already attempted to load previous session
  const hasLoadedSession = useRef(false);

  /**
   * Fetch libraries from API
   * Only called when user opens the form
   */
  const fetchLibraries = async () => {
    // Don't fetch if already fetched or if libraries provided as prop
    if (librariesFetched || (librariesProp && librariesProp.length > 0)) {
      return;
    }

    setIsLoadingLibraries(true);
    try {
      const config = getConfig();
      const baseUrl = config.STUDIO_BASE_URL;
      const endpoint = `${baseUrl}/api/libraries/v2/?pagination=false&order=title`;

      if (debug) {
        logInfo('Fetching libraries from:', endpoint);
      }

      const { data } = await getAuthenticatedHttpClient().get(endpoint);

      // Extract libraries from response
      // API returns array directly (not nested in results)
      const fetchedLibraries = Array.isArray(data) ? data : (data?.results || []);
      setLibraries(fetchedLibraries);
      setLibrariesFetched(true);

      if (debug) {
        logInfo('Fetched libraries:', fetchedLibraries);
      }
    } catch (err) {
      logError('Error fetching libraries:', err);
      setError(intl.formatMessage(messages['ai.extensions.educator.library.loading.error']));
    } finally {
      setIsLoadingLibraries(false);
    }
  };

  // Update libraries when prop changes
  useEffect(() => {
    if (librariesProp && librariesProp.length > 0) {
      setLibraries(librariesProp);
      setLibrariesFetched(true);
    }
  }, [librariesProp]);

  // Preload previous session if enabled
  useEffect(() => {
    const loadPreviousSession = async () => {
      if (!preloadPreviousSession || hasAsked || hasLoadedSession.current) {
        return;
      }

      hasLoadedSession.current = true;
      setIsLoading(true);
      try {
        const contextData = prepareContextData({
          courseId,
          locationId,
        });

        const data = await callWorkflowService({
          context: contextData,
          payload: {
            action: WORKFLOW_ACTIONS.GET_CURRENT_SESSION_RESPONSE,
            requestId: `ai-request-${Date.now()}`,
          },
        });

        // Handle response - only set if there's actual data
        if (data.response && data.response !== null) {
          setResponse(data.response);
          setHasAsked(true);
        } else if (debug) {
          // No previous session or empty response - do nothing, show normal component
          logInfo('No previous session found or empty response');
        }
      } catch (err) {
        // Silent fail - no previous session is not an error
        if (debug) {
          logInfo('Error loading previous session:', err);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadPreviousSession();
  }, [preloadPreviousSession, hasAsked, courseId, locationId, setResponse, setHasAsked, debug]);

  // Early return after all hooks have been called
  if (hasAsked && !isLoading) {
    return null;
  }

  /**
   * Handle form submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (!selectedLibrary) {
      setError(intl.formatMessage(messages['ai.extensions.educator.library.select.error']));
      return;
    }

    if (numberOfQuestions < 1 || numberOfQuestions > 20) {
      setError(intl.formatMessage(messages['ai.extensions.educator.questions.error']));
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Prepare context data (same as AIRequestComponent)
      const contextData = prepareContextData({
        courseId,
        locationId,
      });

      const data = await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.RUN_ASYNC,
          requestId: `ai-request-${Date.now()}`,
          userInput: {
            libraryId: selectedLibrary,
            numQuestions: numberOfQuestions,
            extraInstructions: additionalInstructions,
          },
        },
      });

      if (data.error) {
        throw new Error(data.error);
      }

      // Pass response to response component
      // For async tasks, pass the full response object as JSON
      // Response component will detect status: 'processing' and handle polling
      if (data.status === 'processing' && data.taskId) {
        // Include context data so response component can poll
        setResponse(JSON.stringify({
          ...data,
          courseId,
          locationId,
        }));
      } else {
        // Immediate response
        const immediateResponse = data.response || data.message || data.content
          || data.result || JSON.stringify(data, null, 2);
        setResponse(immediateResponse);
      }

      setHasAsked(true);
      setShowForm(false);

      // Reset form
      setSelectedLibrary('');
      setNumberOfQuestions(5);
      setAdditionalInstructions('');

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      logError('Error generating library questions:', err);

      // Type guard for error
      const submitError = err instanceof Error ? err : new Error(String(err));
      const errorMessage = (err as any)?.response?.data?.error
        || submitError.message
        || intl.formatMessage(messages['ai.extensions.educator.error.questions']);
      setError(errorMessage);

      if (onError) {
        onError(err);
      }
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle form cancellation
   */
  const handleCancel = () => {
    setShowForm(false);
    setError('');
  };

  /**
   * Toggle form visibility
   * Fetch libraries when opening the form
   */
  const handleToggleForm = () => {
    const newShowForm = !showForm;
    setShowForm(newShowForm);
    setError('');

    // Fetch libraries when opening form
    if (newShowForm) {
      fetchLibraries();
    }
  };

  return (
    <Card className="ai-educator-library-assist mt-3 mb-3">
      <Card.Section>
        <div className="ai-library-assist-header">
          <h3 className="d-block mb-1">
            {displayTitle}
          </h3>
          <small className="d-block mb-2 x-small">
            {displayCustomMessage}
          </small>
          <Button
            variant={showForm ? 'outline-secondary' : 'outline-primary'}
            size="sm"
            onClick={handleToggleForm}
            disabled={isLoading}
            iconBefore={showForm ? Close : AutoAwesome}
            className="w-100"
          >
            {showForm ? intl.formatMessage(messages['ai.extensions.educator.cancel']) : displayButtonText}
          </Button>
        </div>

        {/* Error message */}
        {error && (
          <Alert
            variant="danger"
            className="mt-3"
            dismissible
            onClose={() => setError('')}
          >
            {error}
          </Alert>
        )}

        {/* Form */}
        {showForm && (
          <div className="mt-3">
            <Form onSubmit={handleSubmit}>
              {/* Library selection */}
              <Form.Group className="mb-3" size="sm" controlId="library">
                <Form.Label>
                  {intl.formatMessage(messages['ai.extensions.educator.library.label'])}
                  <span className="text-danger">*</span>
                </Form.Label>
                <Form.Control
                  as="select"
                  value={selectedLibrary}
                  onChange={(e) => setSelectedLibrary(e.target.value)}
                  disabled={isLoading || isLoadingLibraries}
                  required
                >
                  <option value="">
                    {isLoadingLibraries
                      ? intl.formatMessage(messages['ai.extensions.educator.library.loading'])
                      : intl.formatMessage(messages['ai.extensions.educator.library.select'])}
                  </option>
                  {libraries && libraries.length > 0 && (
                    libraries.map((library) => (
                      <option key={library.id} value={library.id}>
                        {`${library.id} - ${library.title}`}
                      </option>
                    ))
                  )}
                  {!isLoadingLibraries && (!libraries || libraries.length === 0) && (
                    <option disabled>{intl.formatMessage(messages['ai.extensions.educator.library.none'])}</option>
                  )}
                </Form.Control>
                <Form.Text>
                  <small>{isLoadingLibraries
                    ? intl.formatMessage(messages['ai.extensions.educator.library.help.loading'])
                    : intl.formatMessage(messages['ai.extensions.educator.library.help.select'])}
                  </small>
                </Form.Text>
              </Form.Group>

              {/* Number of questions */}
              <Form.Group className="mb-3" size="sm" controlId="questionNumber">
                <Form.Label>
                  {intl.formatMessage(messages['ai.extensions.educator.questions.label'])}
                  <span className="text-danger">*</span>
                </Form.Label>
                <Form.Control
                  type="number"
                  min="1"
                  max="50"
                  value={numberOfQuestions}
                  onChange={(e) => setNumberOfQuestions(parseInt(e.target.value, 10))}
                  disabled={isLoading}
                  required
                />
                <Form.Text>
                  <small>{intl.formatMessage(messages['ai.extensions.educator.questions.help'])}</small>
                </Form.Text>
              </Form.Group>

              {/* Additional instructions */}
              <Form.Group className="mb-3" size="sm" controlId="additionalInstruction">
                <Form.Label>
                  {intl.formatMessage(messages['ai.extensions.educator.instructions.label'])}
                </Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={additionalInstructions}
                  onChange={(e) => setAdditionalInstructions(e.target.value)}
                  disabled={isLoading}
                  placeholder={intl.formatMessage(messages['ai.extensions.educator.instructions.placeholder'])}
                />
                <Form.Text>
                  <small>{intl.formatMessage(messages['ai.extensions.educator.instructions.help'])}</small>
                </Form.Text>
              </Form.Group>

              {/* Action buttons */}
              <Stack gap={2}>
                <Button
                  variant="primary"
                  type="submit"
                  disabled={isLoading || !selectedLibrary}
                  size="sm"
                  className="w-100"
                >
                  {isLoading ? (
                    <>
                      <Spinner
                        animation="border"
                        size="sm"
                        className="me-2"
                        aria-hidden
                      />
                      {intl.formatMessage(messages['ai.extensions.educator.generating'])}
                    </>
                  ) : (
                    intl.formatMessage(messages['ai.extensions.educator.generate.button'])
                  )}
                </Button>
                <Button
                  variant="outline-secondary"
                  onClick={handleCancel}
                  disabled={isLoading}
                  size="sm"
                  className="w-100"
                >
                  {intl.formatMessage(messages['ai.extensions.educator.cancel'])}
                </Button>
              </Stack>
            </Form>
          </div>
        )}
      </Card.Section>
    </Card>
  );
};

export default AIEducatorLibraryAssistComponent;
