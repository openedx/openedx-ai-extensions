import { useCallback, useReducer } from 'react';
import type { BadgeFormData, GeneratedBadge, FeedbackEntry, WorkflowState, WorkflowStep } from '../types';

type Action =
  | { type: 'RESET' }
  | { type: 'SUBMIT_FORM'; formData: BadgeFormData }
  | { type: 'BADGE_GENERATED'; badge: GeneratedBadge }
  | { type: 'BADGE_REFINED'; badge: GeneratedBadge }
  | { type: 'FEEDBACK_SUBMITTED'; feedback: string }
  | { type: 'BADGE_SAVED'; filePath: string }
  | { type: 'STEP_CHANGED'; step: WorkflowStep }
  | { type: 'LOADING_START' }
  | { type: 'LOADING_END' }
  | { type: 'ERROR_SET'; error: string }
  | { type: 'ERROR_CLEAR' }
  | { type: 'BACK_TO_PREVIEW' };

const initialState: WorkflowState = {
  currentStep: 'input_form',
  formData: {
    title: '',
    description: '',
    criteria: '',
    skillsAligned: '',
    awardConditions: '',
  },
  currentBadge: null,
  feedbackHistory: [],
  isLoading: false,
  error: null,
  saveSuccess: false,
  iterationCount: 0,
};

function reducer(state: WorkflowState, action: Action): WorkflowState {
  switch (action.type) {
    case 'RESET':
      return initialState;
    case 'SUBMIT_FORM':
      return { ...state, formData: action.formData, currentStep: 'generating', isLoading: true, error: null };
    case 'BADGE_GENERATED':
      return { ...state, currentBadge: action.badge, currentStep: 'preview', isLoading: false, iterationCount: 1 };
    case 'FEEDBACK_SUBMITTED':
      return {
        ...state,
        currentStep: 'generating',
        isLoading: true,
        feedbackHistory: [
          ...state.feedbackHistory,
          {
            iteration: state.iterationCount,
            feedback: action.feedback,
            timestamp: new Date().toISOString(),
            generatedBadge: state.currentBadge || undefined,
          },
        ],
      };
    case 'BADGE_REFINED':
      return { ...state, currentBadge: action.badge, currentStep: 'preview', isLoading: false, iterationCount: state.iterationCount + 1 };
    case 'LOADING_START':
      return { ...state, isLoading: true };
    case 'LOADING_END':
      return { ...state, isLoading: false };
    case 'STEP_CHANGED':
      return { ...state, currentStep: action.step };
    case 'ERROR_SET':
      return { ...state, error: action.error, isLoading: false };
    case 'ERROR_CLEAR':
      return { ...state, error: null };
    case 'BADGE_SAVED':
      return { ...state, currentStep: 'complete', isLoading: false, saveSuccess: true };
    case 'BACK_TO_PREVIEW':
      return { ...state, currentStep: 'preview' };
    default:
      return state;
  }
}

export default function useBadgeWorkflowState() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const submitForm = useCallback((formData: BadgeFormData) => dispatch({ type: 'SUBMIT_FORM', formData }), []);
  const badgeGenerated = useCallback((badge: GeneratedBadge) => dispatch({ type: 'BADGE_GENERATED', badge }), []);
  const badgeRefined = useCallback((badge: GeneratedBadge) => dispatch({ type: 'BADGE_REFINED', badge }), []);
  const feedbackSubmitted = useCallback((feedback: string) => dispatch({ type: 'FEEDBACK_SUBMITTED', feedback }), []);
  const badgeSaved = useCallback((filePath: string) => dispatch({ type: 'BADGE_SAVED', filePath }), []);
  const setStep = useCallback((step: WorkflowStep) => dispatch({ type: 'STEP_CHANGED', step }), []);
  const setError = useCallback((error: string) => dispatch({ type: 'ERROR_SET', error }), []);
  const clearError = useCallback(() => dispatch({ type: 'ERROR_CLEAR' }), []);
  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);
  const backToPreview = useCallback(() => dispatch({ type: 'BACK_TO_PREVIEW' }), []);

  return {
    state,
    actions: {
      submitForm,
      badgeGenerated,
      badgeRefined,
      feedbackSubmitted,
      badgeSaved,
      setStep,
      setError,
      clearError,
      reset,
      backToPreview,
    },
  } as const;
}
