/**
 * BadgeCreationWorkflow Component
 * Orchestrates the complete iterative badge creation process
 */

import React, { useCallback } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Container,
  Row,
  Col,
  Spinner,
  Alert,
} from '@openedx/paragon';
import {
  BadgeFormData,
  GeneratedBadge,
} from '../types';
import { useGenerateBadge } from '../data';
import useBadgeWorkflowState from '../hooks/useBadgeWorkflowState';
import BadgeForm from './BadgeForm';
import BadgeDetails from './BadgeDetails';
import BadgeCarousel from './BadgeCarousel';
import messages from '../messages';

interface BadgeCreationWorkflowProps {
  courseId: string;
  courseName?: string;
  onComplete: (badge: GeneratedBadge) => void;
  onError?: (error: string) => void;
  onClose?: () => void;
}

const BadgeCreationWorkflow: React.FC<BadgeCreationWorkflowProps> = ({
  courseId,
  courseName,
  onComplete,
  onError,
  onClose,

}) => {
  const intl = useIntl();
  // Use hooks for API + workflow state
  const api = useGenerateBadge();
  const { state, actions } = useBadgeWorkflowState();

  // Handle form submission
  const handleFormSubmit = async (formData: BadgeFormData) => {
    actions.submitForm(formData);
    try {
      const badge = await api.generate(formData, courseId);
      actions.badgeGenerated(badge);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      actions.setError(errorMsg);
      onError?.(errorMsg);
    }
  };

  // Handle feedback submission for refinement
  const handleFeedbackSubmit = async (feedback: string) => {
    if (!state.currentBadge) return;

    actions.feedbackSubmitted(feedback);
    try {
      const refinedBadge = await api.refine(state.currentBadge, feedback, state.iterationCount);
      actions.badgeRefined(refinedBadge);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      actions.setError(errorMsg);
      onError?.(errorMsg);
    }
  };

  // Handle saving badge
  const handleSave = async () => {
    if (!state.currentBadge) return;

    actions.setStep('saving');
    try {
      const filePath = await api.save(state.currentBadge, state.formData, courseId);
      actions.badgeSaved(filePath);
      onComplete(state.currentBadge);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      actions.setError(errorMsg);
      onError?.(errorMsg);
    }
  };

  // Render different steps
  const renderStep = () => {
    switch (state.currentStep) {
      case 'input_form':
        return (
          <BadgeForm
            onSubmit={handleFormSubmit}
            isLoading={state.isLoading}
            courseId={courseId}
          />
        );

      case 'preview':
      case 'feedback':
        if (!state.currentBadge) {
          return null;
        }
        return (
          <BadgeDetails
            badge={state.currentBadge}
            iterationCount={state.iterationCount}
            isLoading={state.isLoading}
            onRefine={handleFeedbackSubmit}
            onSave={handleSave}
          />
        );

      case 'saving':
      case 'complete':
        // Don't show form during saving or after completion
        return null;

      default:
        return (
          <BadgeForm
            onSubmit={handleFormSubmit}
            isLoading={state.isLoading}
            courseId={courseId}
          />
        );
    }
  };

  // Render right section (preview/carousel)
  const renderPreview = () => {
    if (state.isLoading && state.currentStep === 'generating') {
      return (
        <div className="text-center py-5">
          <Spinner animation="border" className="mb-3" />
          <h5>{intl.formatMessage(messages.generatingTitle)}</h5>
          <p className="text-muted">{intl.formatMessage(messages.generatingMessage)}</p>
        </div>
      );
    }

    if (state.currentStep === 'saving') {
      return (
        <div className="text-center py-5">
          <Spinner animation="border" className="mb-3" />
          <h5>{intl.formatMessage(messages.savingTitle)}</h5>
          <p className="text-muted">{intl.formatMessage(messages.savingMessage)}</p>
        </div>
      );
    }

    if (state.currentStep === 'complete') {
      return (
        <div className="text-center py-5">
          <div className="mb-3" style={{ fontSize: '3rem' }}>✅</div>
          <h5>{intl.formatMessage(messages.completionTitle)}</h5>
          <p className="text-muted mb-4">{intl.formatMessage(messages.completionMessage)}</p>
          <div className="d-flex gap-2 justify-content-center flex-column">
            <button
              type="button"
              className="btn btn-outline-primary"
              onClick={() => {
                actions.reset();
              }}
            >
              {intl.formatMessage(messages.newBadgeButton)}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={onClose}
            >
              {intl.formatMessage(messages.closeButton)}
            </button>
          </div>
        </div>
      );
    }

    // Show carousel for preview/feedback steps with generated badges
    if ((state.currentStep === 'preview' || state.currentStep === 'feedback') && state.currentBadge) {
      const allBadges = [state.currentBadge];
      state.feedbackHistory.forEach((entry) => {
        if (entry.generatedBadge) {
          allBadges.push(entry.generatedBadge);
        }
      });
      return <BadgeCarousel badges={allBadges} currentBadgeId={state.currentBadge.id} />;
    }

    // Placeholder for empty preview
    return (
      <div className="text-center py-5 text-muted">
        <p style={{ fontSize: '3rem' }}>🎖️</p>
        <p>{intl.formatMessage(messages.formStepTitle)}</p>
        <p className="small">Your badge preview will appear here</p>
      </div>
    );
  };

  return (
    <div className="badge-creation-workflow">
      <Container fluid className="h-100">
        <Row className="h-100 g-4">
          {/* Left section: Form */}
          <Col lg={6} className="d-flex flex-column">
            <div className="flex-grow-1 overflow-auto">
              {state.error && (
                <Alert variant="danger" className="mb-4" dismissible onClose={() => actions.clearError()}>
                  {state.error}
                </Alert>
              )}
              {renderStep()}
            </div>
          </Col>

          {/* Right section: Preview */}
          <Col lg={6} className="d-flex flex-column border-start">
            <div className="flex-grow-1 overflow-auto p-4">
              {renderPreview()}
            </div>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default BadgeCreationWorkflow;
