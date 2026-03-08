import {
  useState, useEffect, useRef, useCallback, useMemo,
} from 'react';
import { logError, logInfo } from '@edx/frontend-platform/logging';
import { callWorkflowService, prepareContextData } from '../../services';
import { WORKFLOW_ACTIONS } from '../../constants';

// Polling config (shared with AIEducatorLibraryResponseComponent)
const POLLING_INTERVALS = { INITIAL: 10000, EXTENDED: 30000 };
const POLLING_TIMEOUTS = { SWITCH_TO_EXTENDED: 2, MAX_DURATION: 5 };
const MS_TO_MINUTES = 60000;

export type CreatorStep = 'idle' | 'generating' | 'review' | 'saving' | 'error';

export interface Choice {
  text: string;
  isCorrect: boolean;
  feedback?: string;
}

/** Shape returned by the backend json_to_olx utility */
export interface Olx {
  category: string;
  data: string;
}

export interface Question {
  displayName: string;
  questionHtml: string;
  problemType: string;
  choices: Choice[];
  answerValue?: string;
  tolerance?: string;
  explanation?: string;
  demandHints?: string[];
  olx?: Olx;
}

interface UseLibraryCreatorParams {
  courseId: string;
  locationId: string;
  uiSlotSelectorId?: string | null;
  setResponse: (response: string) => void;
  setHasAsked: (hasAsked: boolean) => void;
  preloadPreviousSession?: boolean;
}

export interface UseLibraryCreatorReturn {
  step: CreatorStep;
  questions: Question[];
  questionHistories: Record<number, Question[]>;
  selectedVersionIndices: Record<number, number>;
  discardedIndices: Set<number>;
  regeneratingIndices: Set<number>;
  editingIndex: number | null;
  collectionName: string;
  setCollectionName: (name: string) => void;
  errorMessage: string;
  generate: (numQuestions: number, extraInstructions?: string) => Promise<void>;
  regenerateQuestion: (index: number, extraInstructions?: string) => Promise<void>;
  selectVersion: (index: number, versionIndex: number) => void;
  updateQuestion: (index: number, updatedQuestion: Question) => void;
  discardQuestion: (index: number) => void;
  restoreQuestion: (index: number) => void;
  setEditingIndex: (index: number | null) => void;
  saveQuestions: (libraryId: string) => Promise<void>;
  startOver: () => Promise<void>;
}

export function useLibraryCreator({
  courseId,
  locationId,
  uiSlotSelectorId,
  setResponse,
  setHasAsked,
  preloadPreviousSession = false,
}: UseLibraryCreatorParams): UseLibraryCreatorReturn {
  const [step, setStep] = useState<CreatorStep>('idle');
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionHistories, setQuestionHistories] = useState<Record<number, Question[]>>({});
  const [selectedVersionIndices, setSelectedVersionIndices] = useState<Record<number, number>>({});
  const [discardedIndices, setDiscardedIndices] = useState<Set<number>>(new Set());
  const [regeneratingIndices, setRegeneratingIndices] = useState<Set<number>>(new Set());
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [collectionName, setCollectionName] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollingStartTimeRef = useRef<number | null>(null);
  const hasLoadedSession = useRef(false);

  const contextData = useMemo(() => prepareContextData({
    courseId,
    locationId,
    uiSlotSelectorId,
  }), [courseId, locationId, uiSlotSelectorId]);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const handleQuestionsResponse = useCallback((response: any) => {
    const name: string = response.collectionName || '';
    // question_slots → [{versions: [...], selected: N}]
    const slots: Array<{ versions: Question[]; selected: number }> = response.questionSlots || [];
    const qs: Question[] = slots.map((slot) => slot.versions[slot.selected]);
    const initHistories: Record<number, Question[]> = {};
    const initIndices: Record<number, number> = {};
    slots.forEach((slot, i) => {
      initHistories[i] = slot.versions;
      initIndices[i] = slot.selected;
    });
    setQuestions(qs);
    setCollectionName(name);
    setDiscardedIndices(new Set());
    setEditingIndex(null);
    setQuestionHistories(initHistories);
    setSelectedVersionIndices(initIndices);
    setStep('review');
  }, []);

  const pollTaskStatus = useCallback(async (taskId: string) => {
    try {
      const data = await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.GET_RUN_STATUS,
          requestId: `ai-poll-${Date.now()}`,
          taskId,
          courseId,
        },
      });

      if (data.status === 'completed' || data.status === 'success') {
        stopPolling();
        const responseData = data.response;
        if (responseData && typeof responseData === 'object' && responseData.questionSlots) {
          handleQuestionsResponse(responseData);
        } else {
          setErrorMessage('Unexpected response format from generation task.');
          setStep('error');
        }
      } else if (data.status === 'error' || data.status === 'timeout' || data.error) {
        stopPolling();
        setErrorMessage(data.error || data.message || 'Generation failed.');
        setStep('error');
      }
    } catch (err) {
      logError('useLibraryCreator: poll error:', err);
      // Don't stop on a single poll error
    }
  }, [contextData, courseId, handleQuestionsResponse, stopPolling]);

  const startPolling = useCallback((taskId: string) => {
    pollingStartTimeRef.current = Date.now();
    pollTaskStatus(taskId);

    let pollCount = 0;
    pollingIntervalRef.current = setInterval(() => {
      if (!pollingStartTimeRef.current) { return; }
      const elapsedMinutes = (Date.now() - pollingStartTimeRef.current) / MS_TO_MINUTES;
      pollCount += 1;

      if (elapsedMinutes >= POLLING_TIMEOUTS.MAX_DURATION) {
        stopPolling();
        setErrorMessage('Generation timed out. Please try again.');
        setStep('error');
        return;
      }

      if (elapsedMinutes >= POLLING_TIMEOUTS.SWITCH_TO_EXTENDED && pollCount === 12) {
        stopPolling();
        pollingIntervalRef.current = setInterval(() => pollTaskStatus(taskId), POLLING_INTERVALS.EXTENDED);
        return;
      }

      pollTaskStatus(taskId);
    }, POLLING_INTERVALS.INITIAL);
  }, [pollTaskStatus, stopPolling]);

  // Preload previous session
  useEffect(() => {
    if (!preloadPreviousSession || hasLoadedSession.current) { return; }
    hasLoadedSession.current = true;

    const load = async () => {
      try {
        const data = await callWorkflowService({
          context: contextData,
          payload: {
            action: WORKFLOW_ACTIONS.GET_CURRENT_SESSION_RESPONSE,
            requestId: `ai-request-${Date.now()}`,
          },
        });

        if (!data.response) { return; }

        if (typeof data.response === 'string') {
          // Already saved — show response component
          setResponse(data.response);
          setHasAsked(true);
        } else if (typeof data.response === 'object' && data.response.questionSlots) {
          // Questions waiting for review
          handleQuestionsResponse(data.response);
        }
      } catch (err) {
        logInfo('useLibraryCreator: no previous session', err);
      }
    };

    load();
  }, [preloadPreviousSession, contextData, setResponse, setHasAsked, handleQuestionsResponse]);

  // Cleanup polling on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  const generate = useCallback(async (numQuestions: number, extraInstructions?: string) => {
    setStep('generating');
    setErrorMessage('');
    try {
      const data = await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.RUN_ASYNC,
          requestId: `ai-request-${Date.now()}`,
          userInput: {
            numQuestions,
            ...(extraInstructions ? { extraInstructions } : {}),
          },
        },
      });

      if (data.status === 'processing' && data.taskId) {
        startPolling(data.taskId);
      } else if (data.status === 'completed' && data.response) {
        handleQuestionsResponse(data.response);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        setErrorMessage('Unexpected response. Please try again.');
        setStep('error');
      }
    } catch (err) {
      logError('useLibraryCreator: generate error:', err);
      setErrorMessage((err as Error).message || 'Failed to generate questions.');
      setStep('error');
    }
  }, [contextData, startPolling, handleQuestionsResponse]);

  const regenerateQuestion = useCallback(async (index: number, extraInstructions?: string) => {
    setRegeneratingIndices((prev) => new Set(prev).add(index));
    try {
      const data = await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.REGENERATE_QUESTION,
          requestId: `ai-request-${Date.now()}`,
          userInput: {
            questionIndex: index,
            ...(extraInstructions ? { extraInstructions } : {}),
          },
        },
      });

      if (data.status === 'completed' && data.response) {
        const newQuestion = data.response.question as Question;
        // Backend returns the full updated versions array and the selected index for this slot
        const slotHistory = (data.response.history as Question[]) || [...(questionHistories[index] || []), newQuestion];
        const newVersionIndex = typeof data.response.selected === 'number'
          ? data.response.selected
          : slotHistory.length - 1;
        setQuestions((prev) => {
          const next = [...prev];
          next[index] = newQuestion;
          return next;
        });
        setQuestionHistories((prev) => ({ ...prev, [index]: slotHistory }));
        setSelectedVersionIndices((prev) => ({ ...prev, [index]: newVersionIndex }));
        // Remove from discarded if it was discarded
        setDiscardedIndices((prev) => {
          const next = new Set(prev);
          next.delete(index);
          return next;
        });
      } else if (data.error) {
        logError('useLibraryCreator: regenerate error:', data.error);
      }
    } catch (err) {
      logError('useLibraryCreator: regenerate error:', err);
    } finally {
      setRegeneratingIndices((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  }, [contextData]);

  const selectVersion = useCallback((index: number, versionIndex: number) => {
    const history = questionHistories[index];
    if (!history || versionIndex < 0 || versionIndex >= history.length) { return; }
    setSelectedVersionIndices((prev) => ({ ...prev, [index]: versionIndex }));
    setQuestions((prev) => {
      const next = [...prev];
      next[index] = history[versionIndex];
      return next;
    });
  }, [questionHistories]);

  const updateQuestion = useCallback((index: number, updatedQuestion: Question) => {
    setQuestions((prev) => {
      const next = [...prev];
      next[index] = updatedQuestion;
      return next;
    });
  }, []);

  const discardQuestion = useCallback((index: number) => {
    setDiscardedIndices((prev) => new Set(prev).add(index));
    setEditingIndex((prev) => (prev === index ? null : prev));
  }, []);

  const restoreQuestion = useCallback((index: number) => {
    setDiscardedIndices((prev) => {
      const next = new Set(prev);
      next.delete(index);
      return next;
    });
  }, []);

  const saveQuestions = useCallback(async (libraryId: string) => {
    const activeQuestions = questions.filter((_, i) => !discardedIndices.has(i));
    setStep('saving');
    setErrorMessage('');
    try {
      const data = await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.SAVE,
          requestId: `ai-request-${Date.now()}`,
          userInput: {
            libraryId,
            questions: activeQuestions,
            collectionName,
          },
        },
      });

      if (data.status === 'completed' && data.response) {
        setStep('idle');
        setQuestions([]);
        setQuestionHistories({});
        setSelectedVersionIndices({});
        setDiscardedIndices(new Set());
        setResponse(data.response as string);
        setHasAsked(true);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        throw new Error('Unexpected save response.');
      }
    } catch (err) {
      logError('useLibraryCreator: save error:', err);
      setErrorMessage((err as Error).message || 'Failed to save questions.');
      setStep('review');
    }
  }, [contextData, questions, discardedIndices, collectionName, setResponse, setHasAsked]);

  const startOver = useCallback(async () => {
    stopPolling();
    try {
      await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.CLEAR_SESSION,
          requestId: `ai-request-${Date.now()}`,
        },
      });
    } catch (err) {
      logInfo('useLibraryCreator: clear session error (non-fatal):', err);
    }
    setStep('idle');
    setQuestions([]);
    setQuestionHistories({});
    setSelectedVersionIndices({});
    setDiscardedIndices(new Set());
    setRegeneratingIndices(new Set());
    setEditingIndex(null);
    setCollectionName('');
    setErrorMessage('');
  }, [contextData, stopPolling]);

  return {
    step,
    questions,
    questionHistories,
    selectedVersionIndices,
    discardedIndices,
    regeneratingIndices,
    editingIndex,
    collectionName,
    setCollectionName,
    errorMessage,
    generate,
    regenerateQuestion,
    selectVersion,
    updateQuestion,
    discardQuestion,
    restoreQuestion,
    setEditingIndex,
    saveQuestions,
    startOver,
  };
}

export default useLibraryCreator;
