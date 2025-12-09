import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  Form,
  Spinner,
  Alert,
  Card,
} from '@openedx/paragon';
import { AutoAwesome, Close } from '@openedx/paragon/icons';
import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import { callWorkflowService, prepareContextData } from '../services';

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
  preloadPreviousSession,
  customMessage,
  onSuccess,
  onError,
  debug,
}) => {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

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
        // eslint-disable-next-line no-console
        console.log('Fetching libraries from:', endpoint);
      }

      const { data } = await getAuthenticatedHttpClient().get(endpoint);

      // Extract libraries from response
      // API returns array directly (not nested in results)
      const fetchedLibraries = Array.isArray(data) ? data : (data?.results || []);
      setLibraries(fetchedLibraries);
      setLibrariesFetched(true);

      if (debug) {
        // eslint-disable-next-line no-console
        console.log('Fetched libraries:', fetchedLibraries);
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Error fetching libraries:', err);
      setError('Failed to load libraries. Please try again.');
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
          action: 'get_current_session_response',
          payload: {
            requestId: `ai-request-${Date.now()}`,
            courseId,
          },
        });

        // Handle response - only set if there's actual data
        if (data.response && data.response !== null) {
          setResponse(data.response);
          setHasAsked(true);
        } else if (debug) {
          // No previous session or empty response - do nothing, show normal component
          // eslint-disable-next-line no-console
          console.log('No previous session found or empty response');
        }
      } catch (err) {
        // Silent fail - no previous session is not an error
        if (debug) {
          // eslint-disable-next-line no-console
          console.log('Error loading previous session:', err);
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
      setError('Please select a library');
      return;
    }

    if (numberOfQuestions < 1 || numberOfQuestions > 20) {
      setError('Number of questions must be between 1 and 20');
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
        action: 'run',
        payload: {
          requestId: `ai-request-${Date.now()}`,
          courseId,
          user_input: {
            library_id: selectedLibrary,
            num_questions: numberOfQuestions,
            extra_instructions: additionalInstructions,
          },
        },
      });

      // Handle response
      if (data.response) {
        setResponse(data.response);
        setHasAsked(true);
      } else if (data.message) {
        setResponse(data.message);
        setHasAsked(true);
      } else if (data.content) {
        setResponse(data.content);
        setHasAsked(true);
      } else if (data.result) {
        setResponse(data.result);
        setHasAsked(true);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        setResponse(JSON.stringify(data, null, 2));
        setHasAsked(true);
      }
      setShowForm(false);

      // Reset form
      setSelectedLibrary('');
      setNumberOfQuestions(5);
      setAdditionalInstructions('');

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Error generating library questions:', err);
      const errorMessage = err.response?.data?.error
        || err.message
        || 'Failed to generate questions. Please try again.';
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
          <h3 className="d-block mb-1" style={{ fontSize: '1.25rem' }}>
            {titleText}
          </h3>
          <small className="d-block mb-2" style={{ fontSize: '0.75rem' }}>
            {customMessage}
          </small>
          <Button
            variant={showForm ? 'outline-secondary' : 'outline-primary'}
            size="sm"
            onClick={handleToggleForm}
            disabled={isLoading}
            iconBefore={showForm ? Close : AutoAwesome}
            className="w-100"
          >
            {showForm ? 'Cancel' : buttonText}
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
              <Form.Group className="mb-3">
                <Form.Label>
                  <small>
                    Library
                    <span className="text-danger">*</span>
                  </small>
                </Form.Label>
                <Form.Control
                  as="select"
                  value={selectedLibrary}
                  onChange={(e) => setSelectedLibrary(e.target.value)}
                  disabled={isLoading || isLoadingLibraries}
                  required
                  size="sm"
                >
                  <option value="">
                    {isLoadingLibraries ? 'Loading libraries...' : 'Select a library...'}
                  </option>
                  {libraries && libraries.length > 0 && (
                    libraries.map((library) => (
                      <option key={library.id} value={library.id}>
                        {`${library.id} - ${library.title}`}
                      </option>
                    ))
                  )}
                  {!isLoadingLibraries && (!libraries || libraries.length === 0) && (
                    <option disabled>No libraries available</option>
                  )}
                </Form.Control>
                <Form.Text className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {isLoadingLibraries
                    ? 'Loading available libraries...'
                    : 'Select the library where questions will be added'}
                </Form.Text>
              </Form.Group>

              {/* Number of questions */}
              <Form.Group className="mb-3">
                <Form.Label>
                  <small>
                    Number of Questions
                    <span className="text-danger">*</span>
                  </small>
                </Form.Label>
                <Form.Control
                  type="number"
                  min="1"
                  max="50"
                  value={numberOfQuestions}
                  onChange={(e) => setNumberOfQuestions(parseInt(e.target.value, 10))}
                  disabled={isLoading}
                  required
                  size="sm"
                />
                <Form.Text className="text-muted" style={{ fontSize: '0.75rem' }}>
                  Number of questions to generate (1-50)
                </Form.Text>
              </Form.Group>

              {/* Additional instructions */}
              <Form.Group className="mb-3">
                <Form.Label>
                  <small>Additional Instructions (Optional)</small>
                </Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={additionalInstructions}
                  onChange={(e) => setAdditionalInstructions(e.target.value)}
                  disabled={isLoading}
                  placeholder="Add any specific instructions for the AI..."
                  style={{ fontSize: '0.875rem' }}
                />
                <Form.Text className="text-muted" style={{ fontSize: '0.75rem' }}>
                  Provide additional context or instructions for question generation
                </Form.Text>
              </Form.Group>

              {/* Action buttons */}
              <div className="d-flex flex-column gap-2">
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
                        as="span"
                      />
                      Generating...
                    </>
                  ) : (
                    'Generate Questions'
                  )}
                </Button>
                <Button
                  variant="outline-secondary"
                  onClick={handleCancel}
                  disabled={isLoading}
                  size="sm"
                  className="w-100"
                >
                  Cancel
                </Button>
              </div>
            </Form>
          </div>
        )}
      </Card.Section>
    </Card>
  );
};

AIEducatorLibraryAssistComponent.propTypes = {
  courseId: PropTypes.string.isRequired,
  locationId: PropTypes.string.isRequired,
  hasAsked: PropTypes.bool.isRequired,
  setResponse: PropTypes.func.isRequired,
  setHasAsked: PropTypes.func.isRequired,
  libraries: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
    }),
  ),
  titleText: PropTypes.string,
  buttonText: PropTypes.string,
  preloadPreviousSession: PropTypes.bool,
  customMessage: PropTypes.string,
  onSuccess: PropTypes.func,
  onError: PropTypes.func,
  debug: PropTypes.bool,
};

AIEducatorLibraryAssistComponent.defaultProps = {
  libraries: null,
  titleText: 'AI Assistant',
  buttonText: 'Start',
  customMessage: 'Use an AI workflow to create multiple answer questions from this unit in a content library',
  preloadPreviousSession: false,
  onSuccess: null,
  onError: null,
  debug: false,
};

export default AIEducatorLibraryAssistComponent;
