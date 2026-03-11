import React, {
  createContext, useContext, useState, useEffect, useRef, useCallback, useMemo,
} from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { logError, logInfo } from '@edx/frontend-platform/logging';
import { prepareContextData } from '../../services';
import messages from '../messages';
import { Library } from '../data/library';
import {
  generateQuestions, regenerateQuestion as regenerateQuestionApi,
  saveToLibrary, getSessionResponse, clearSession,
} from '../data/workflowActions';
import { useLibraryPicker } from '../hooks/useLibraryPicker';
import { useAsyncTaskPolling } from '../hooks/useAsyncTaskPolling';
import type {
  CreatorStep, Choice, Olx, Question,
} from '../types';

export type {
  CreatorStep, Choice, Olx, Question,
};

// ─── Context value shape ──────────────────────────────────────────────────────
interface LibraryProblemCreatorContextValue {
  // Core state
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
  // Core actions
  generate: (numQuestions: number, extraInstructions?: string) => Promise<void>;
  regenerateQuestion: (index: number, extraInstructions?: string) => Promise<void>;
  selectVersion: (index: number, versionIndex: number) => void;
  updateQuestion: (index: number, updatedQuestion: Question) => void;
  discardQuestion: (index: number) => void;
  restoreQuestion: (index: number) => void;
  setEditingIndex: (index: number | null) => void;
  saveQuestions: (libraryId: string) => Promise<void>;
  startOver: () => Promise<void>;
  // Library picker
  libraries: Library[];
  selectedLibrary: string;
  libraryError: string;
  isLoadingLibraries: boolean;
  setSelectedLibrary: (lib: string) => void;
  setLibraryError: (err: string) => void;
  fetchLibraries: () => Promise<void>;
  // Derived / UI handlers
  activeCount: number;
  handleSave: () => void;
  handleStartOver: () => Promise<void>;
  /** Optional external code-editor component (e.g. CodeMirror) for OLX editing */
  CodeEditor?: React.ComponentType<any> | null;
}

// ─── Provider props ───────────────────────────────────────────────────────────
export interface LibraryProblemCreatorProviderProps {
  courseId: string;
  locationId: string;
  uiSlotSelectorId?: string | null;
  setResponse: (response: string) => void;
  setHasAsked: (hasAsked: boolean) => void;
  preloadPreviousSession?: boolean;
  CodeEditor?: React.ComponentType<any> | null;
  children: React.ReactNode;
}

// ─── Context ──────────────────────────────────────────────────────────────────
const LibraryProblemCreatorContext = createContext<LibraryProblemCreatorContextValue | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────────
export const LibraryProblemCreatorProvider = ({
  courseId,
  locationId,
  uiSlotSelectorId = null,
  setResponse,
  setHasAsked,
  preloadPreviousSession = false,
  CodeEditor = null,
  children,
}: LibraryProblemCreatorProviderProps) => {
  const intl = useIntl();

  // Core state
  const [step, setStep] = useState<CreatorStep>('idle');
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionHistories, setQuestionHistories] = useState<Record<number, Question[]>>({});
  const [selectedVersionIndices, setSelectedVersionIndices] = useState<Record<number, number>>({});
  const [discardedIndices, setDiscardedIndices] = useState<Set<number>>(new Set());
  const [regeneratingIndices, setRegeneratingIndices] = useState<Set<number>>(new Set());
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [collectionName, setCollectionName] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Library picker
  const {
    libraries,
    selectedLibrary,
    libraryError,
    isLoadingLibraries,
    setSelectedLibrary,
    setLibraryError,
    fetchLibraries,
  } = useLibraryPicker();

  const hasLoadedSession = useRef(false);

  const contextData = useMemo(() => prepareContextData({
    courseId,
    locationId,
    uiSlotSelectorId,
  }), [courseId, locationId, uiSlotSelectorId]);

  // ── Question response handler ──────────────────────────────────────────────
  const handleQuestionsResponse = useCallback((response: any, preloaded = false) => {
    const name: string = response.collectionName || '';
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
    setStep(preloaded ? 'preloaded' : 'review');
  }, []);

  // ── Polling (delegated to hook) ────────────────────────────────────────────
  const handlePollingError = useCallback((message: string) => {
    setErrorMessage(message);
    setStep('error');
  }, []);

  const { startPolling, stopPolling } = useAsyncTaskPolling({
    contextData,
    courseId,
    onComplete: handleQuestionsResponse,
    onError: handlePollingError,
  });

  // ── Effects ────────────────────────────────────────────────────────────────

  // Preload previous session
  useEffect(() => {
    if (!preloadPreviousSession || hasLoadedSession.current) { return; }
    hasLoadedSession.current = true;

    const load = async () => {
      try {
        const data = await getSessionResponse({ context: contextData });

        const resp = data.response as any;
        if (!resp) { return; }

        if (typeof resp === 'string') {
          setResponse(resp);
          setHasAsked(true);
        } else if (typeof resp === 'object' && resp.questionSlots) {
          handleQuestionsResponse(resp, true);
        }
      } catch (err) {
        logInfo('LibraryProblemCreatorProvider: no previous session', err);
      }
    };

    load();
  }, [preloadPreviousSession, contextData, setResponse, setHasAsked, handleQuestionsResponse]);

  // ── Core actions ───────────────────────────────────────────────────────────
  const generate = useCallback(async (numQuestions: number, extraInstructions?: string) => {
    setStep('generating');
    setErrorMessage('');
    try {
      const data = await generateQuestions({
        context: contextData,
        numQuestions,
        extraInstructions,
      });

      if (data.status === 'processing' && data.taskId) {
        startPolling(data.taskId);
      } else if (data.status === 'completed' && data.response) {
        handleQuestionsResponse(data.response);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        setErrorMessage(intl.formatMessage(messages['ai.library.creator.error.unexpected.response']));
        setStep('error');
      }
    } catch (err) {
      logError('LibraryProblemCreatorProvider: generate error:', err);
      setErrorMessage((err as Error).message || intl.formatMessage(messages['ai.library.creator.error.generate']));
      setStep('error');
    }
  }, [contextData, startPolling, handleQuestionsResponse, intl]);

  const regenerateQuestion = useCallback(async (index: number, extraInstructions?: string) => {
    setRegeneratingIndices((prev) => new Set(prev).add(index));
    try {
      const data = await regenerateQuestionApi({
        context: contextData,
        questionIndex: index,
        extraInstructions,
      });

      const resp = data.response as any;
      if (data.status === 'completed' && resp) {
        const newQuestion = resp.question as Question;
        const slotHistory = (resp.history as Question[]) || [...(questionHistories[index] || []), newQuestion];
        const newVersionIndex = typeof resp.selected === 'number'
          ? resp.selected
          : slotHistory.length - 1;
        setQuestions((prev) => {
          const next = [...prev];
          next[index] = newQuestion;
          return next;
        });
        setQuestionHistories((prev) => ({ ...prev, [index]: slotHistory }));
        setSelectedVersionIndices((prev) => ({ ...prev, [index]: newVersionIndex }));
        setDiscardedIndices((prev) => {
          const next = new Set(prev);
          next.delete(index);
          return next;
        });
      } else if (data.error) {
        logError('LibraryProblemCreatorProvider: regenerate error:', data.error);
        setErrorMessage(data.error || intl.formatMessage(messages['ai.library.creator.error.generate']));
      }
    } catch (err) {
      logError('LibraryProblemCreatorProvider: regenerate error:', err);
      setErrorMessage((err as Error).message || intl.formatMessage(messages['ai.library.creator.error.generate']));
    } finally {
      setRegeneratingIndices((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  }, [contextData, questionHistories, intl]);

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
      const data = await saveToLibrary({
        context: contextData,
        libraryId,
        questions: activeQuestions,
        collectionName,
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
        throw new Error(intl.formatMessage(messages['ai.library.creator.error.unexpected.save']));
      }
    } catch (err) {
      logError('LibraryProblemCreatorProvider: save error:', err);
      setErrorMessage((err as Error).message || intl.formatMessage(messages['ai.library.creator.error.save']));
      setStep('review');
    }
  }, [contextData, questions, discardedIndices, collectionName, setResponse, setHasAsked, intl]);

  const startOver = useCallback(async () => {
    stopPolling();
    try {
      await clearSession({ context: contextData });
    } catch (err) {
      logInfo('LibraryProblemCreatorProvider: clear session error (non-fatal):', err);
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

  // ── UI handlers (convenience wrappers used by child components) ───────────────
  const activeCount = questions.length - discardedIndices.size;

  const handleSave = useCallback(() => {
    if (!selectedLibrary) {
      setLibraryError(intl.formatMessage(messages['ai.library.creator.error.no.library']));
      return;
    }
    if (activeCount === 0) {
      setLibraryError(intl.formatMessage(messages['ai.library.creator.error.no.questions']));
      return;
    }
    setLibraryError('');
    saveQuestions(selectedLibrary);
  }, [selectedLibrary, activeCount, saveQuestions, setLibraryError, intl]);

  const handleStartOver = useCallback(async () => {
    setSelectedLibrary('');
    setLibraryError('');
    await startOver();
  }, [startOver, setSelectedLibrary, setLibraryError]);

  // ── Context value ─────────────────────────────────────────────────────────────
  const value = useMemo<LibraryProblemCreatorContextValue>(() => ({
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
    libraries,
    selectedLibrary,
    libraryError,
    isLoadingLibraries,
    setSelectedLibrary,
    setLibraryError,
    fetchLibraries,
    activeCount,
    handleSave,
    handleStartOver,
    CodeEditor,
  }), [
    step, questions, questionHistories, selectedVersionIndices, discardedIndices,
    regeneratingIndices, editingIndex, collectionName, errorMessage,
    generate, regenerateQuestion, selectVersion, updateQuestion, discardQuestion,
    restoreQuestion, saveQuestions, startOver,
    libraries, selectedLibrary, libraryError, isLoadingLibraries,
    setSelectedLibrary, setLibraryError, fetchLibraries,
    activeCount, handleSave, handleStartOver,
    CodeEditor,
  ]);

  return (
    <LibraryProblemCreatorContext.Provider value={value}>
      {children}
    </LibraryProblemCreatorContext.Provider>
  );
};

// ─── Consumer hook ────────────────────────────────────────────────────────────
export const useLibraryProblemCreatorContext = (): LibraryProblemCreatorContextValue => {
  const ctx = useContext(LibraryProblemCreatorContext);
  if (!ctx) {
    throw new Error('useLibraryProblemCreatorContext must be used inside LibraryProblemCreatorProvider');
  }
  return ctx;
};
