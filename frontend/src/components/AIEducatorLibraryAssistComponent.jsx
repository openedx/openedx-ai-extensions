import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  Form,
  Spinner,
  Alert,
  Card,
} from '@openedx/paragon';
import { AutoAwesome, Close } from '@openedx/paragon/icons';
import { callWorkflowService } from '../services';

/**
 * AI Educator Library Assist Component
 * Allows educators to generate questions for the current unit using AI
 * and add them to a selected library
 */
const AIEducatorLibraryAssistComponent = ({
  courseId,
  unitId,
  libraries,
  titleText,
  buttonText,
  customMessage,
  onSuccess,
  onError,
  debug,
}) => {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [selectedLibrary, setSelectedLibrary] = useState('');
  const [numberOfQuestions, setNumberOfQuestions] = useState(5);
  const [additionalInstructions, setAdditionalInstructions] = useState('');

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
      setError('Number of questions must be between 1 and 50');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const payload = {
        library_id: selectedLibrary,
        num_questions: numberOfQuestions,
        additional_instructions: additionalInstructions || undefined,
        course_id: courseId,
        unit_id: unitId,
      };

      if (debug) {
        // eslint-disable-next-line no-console
        console.log('Submitting library question generation request:', payload);
      }

      await callWorkflowService({
        workflowType: 'generate_library_questions',
        payload,
      });

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
   */
  const handleToggleForm = () => {
    setShowForm(!showForm);
    setError('');
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
                  disabled={isLoading}
                  required
                  size="sm"
                >
                  <option value="">Select a library...</option>
                  {libraries && libraries.length > 0 ? (
                    libraries.map((library) => (
                      <option key={library.id} value={library.id}>
                        {library.name || library.id}
                      </option>
                    ))
                  ) : (
                    <option disabled>No libraries available</option>
                  )}
                </Form.Control>
                <Form.Text className="text-muted" style={{ fontSize: '0.75rem' }}>
                  Select the library where questions will be added
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
  unitId: PropTypes.string.isRequired,
  libraries: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string,
    }),
  ).isRequired,
  titleText: PropTypes.string,
  buttonText: PropTypes.string,
  customMessage: PropTypes.string,
  onSuccess: PropTypes.func,
  onError: PropTypes.func,
  debug: PropTypes.bool,
};

AIEducatorLibraryAssistComponent.defaultProps = {
  titleText: 'AI Assistant',
  buttonText: 'Start',
  customMessage: 'Use an AI workflow to create multiple answer questions from this unit in a content library',
  onSuccess: null,
  onError: null,
  debug: false,
};

export default AIEducatorLibraryAssistComponent;
