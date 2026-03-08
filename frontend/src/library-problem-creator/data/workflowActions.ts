import { callWorkflowService } from '../../services';
import { WORKFLOW_ACTIONS } from '../../constants';
import { Question } from '../types';

interface ContextParam {
  context: Record<string, any>;
}

// ── Generate (async) ─────────────────────────────────────────────────────────

interface GenerateParams extends ContextParam {
  numQuestions: number;
  extraInstructions?: string;
}

export async function generateQuestions({
  context, numQuestions, extraInstructions,
}: GenerateParams) {
  return callWorkflowService({
    context,
    payload: {
      action: WORKFLOW_ACTIONS.RUN_ASYNC,
      requestId: `ai-request-${Date.now()}`,
      userInput: {
        numQuestions,
        ...(extraInstructions ? { extraInstructions } : {}),
      },
    },
  });
}

// ── Poll task status ─────────────────────────────────────────────────────────

interface PollParams extends ContextParam {
  taskId: string;
  courseId: string;
}

export async function pollTaskStatus({
  context, taskId, courseId,
}: PollParams) {
  return callWorkflowService({
    context,
    payload: {
      action: WORKFLOW_ACTIONS.GET_RUN_STATUS,
      requestId: `ai-poll-${Date.now()}`,
      taskId,
      courseId,
    },
  });
}

// ── Regenerate a single question ─────────────────────────────────────────────

interface RegenerateParams extends ContextParam {
  questionIndex: number;
  extraInstructions?: string;
}

export async function regenerateQuestion({
  context, questionIndex, extraInstructions,
}: RegenerateParams) {
  return callWorkflowService({
    context,
    payload: {
      action: WORKFLOW_ACTIONS.REGENERATE_QUESTION,
      requestId: `ai-request-${Date.now()}`,
      userInput: {
        questionIndex,
        ...(extraInstructions ? { extraInstructions } : {}),
      },
    },
  });
}

// ── Save questions to library ────────────────────────────────────────────────

interface SaveParams extends ContextParam {
  libraryId: string;
  questions: Question[];
  collectionName: string;
}

export async function saveToLibrary({
  context, libraryId, questions, collectionName,
}: SaveParams) {
  return callWorkflowService({
    context,
    payload: {
      action: WORKFLOW_ACTIONS.SAVE,
      requestId: `ai-request-${Date.now()}`,
      userInput: {
        libraryId,
        questions,
        collectionName,
      },
    },
  });
}

// ── Get current session response ─────────────────────────────────────────────

export async function getSessionResponse({ context }: ContextParam) {
  return callWorkflowService({
    context,
    payload: {
      action: WORKFLOW_ACTIONS.GET_CURRENT_SESSION_RESPONSE,
      requestId: `ai-request-${Date.now()}`,
    },
  });
}

// ── Clear session ────────────────────────────────────────────────────────────

export async function clearSession({ context }: ContextParam) {
  return callWorkflowService({
    context,
    payload: {
      action: WORKFLOW_ACTIONS.CLEAR_SESSION,
      requestId: `ai-request-${Date.now()}`,
    },
  });
}
