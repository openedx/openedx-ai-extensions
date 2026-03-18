import { callWorkflowService } from '../../services';
import { WORKFLOW_ACTIONS } from '../../constants';
import { CardStack } from '../types';

interface ContextParam {
  context: Record<string, any>;
}

// ── Generate flashcards (async) ─────────────────────────────────────────────

interface GenerateParams extends ContextParam {
  numCards: number | null;
}

export const generateFlashcards = async ({
  context, numCards,
}: GenerateParams) => callWorkflowService({
  context,
  payload: {
    action: WORKFLOW_ACTIONS.RUN_ASYNC,
    requestId: `ai-request-${Date.now()}`,
    userInput: { numCards },
  },
});

// ── Poll task status ────────────────────────────────────────────────────────

interface PollParams extends ContextParam {
  taskId: string;
  courseId: string;
}

export const pollTaskStatus = async ({
  context, taskId, courseId,
}: PollParams) => callWorkflowService({
  context,
  payload: {
    action: WORKFLOW_ACTIONS.GET_RUN_STATUS,
    requestId: `ai-poll-${Date.now()}`,
    taskId,
    courseId,
  },
});

// ── Save card stack ─────────────────────────────────────────────────────────

interface SaveParams extends ContextParam {
  cardStack: CardStack;
}

export const saveCardStack = async ({
  context, cardStack,
}: SaveParams) => callWorkflowService({
  context,
  payload: {
    action: WORKFLOW_ACTIONS.SAVE,
    requestId: `ai-request-${Date.now()}`,
    userInput: { cardStack },
  },
});

// ── Get current session response ────────────────────────────────────────────

export const getSessionResponse = async ({ context }: ContextParam) => callWorkflowService({
  context,
  payload: {
    action: WORKFLOW_ACTIONS.GET_CURRENT_SESSION_RESPONSE,
    requestId: `ai-request-${Date.now()}`,
  },
});

// ── Clear session ───────────────────────────────────────────────────────────

export const clearSession = async ({ context }: ContextParam) => callWorkflowService({
  context,
  payload: {
    action: WORKFLOW_ACTIONS.CLEAR_SESSION,
    requestId: `ai-request-${Date.now()}`,
  },
});
