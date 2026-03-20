import { callWorkflowService } from '../../services';
import { WORKFLOW_ACTIONS } from '../../constants';
import {
  generateFlashcards, pollTaskStatus, saveCardStack, getSessionResponse, clearSession,
} from './workflowActions';

jest.mock('../../services', () => ({
  callWorkflowService: jest.fn(),
}));

const mockCallWorkflow = callWorkflowService as jest.Mock;
const context = {
  courseId: 'course-v1:Org+Course+Run',
  locationId: 'block-v1:Org+Course+Run+type@unit+block@abc',
  uiSlotSelectorId: 'openedx.learning.unit.header.slot.v1',
};

describe('generateFlashcards', () => {
  it('sends RUN_ASYNC with numCards in userInput', async () => {
    mockCallWorkflow.mockResolvedValue({ status: 'processing', taskId: 'task-1' });

    await generateFlashcards({ context, numCards: 5 });

    expect(mockCallWorkflow).toHaveBeenCalledWith({
      context,
      payload: expect.objectContaining({
        action: WORKFLOW_ACTIONS.RUN_ASYNC,
        userInput: { numCards: 5 },
      }),
    });
  });
});

describe('pollTaskStatus', () => {
  it('sends GET_RUN_STATUS with taskId and courseId', async () => {
    mockCallWorkflow.mockResolvedValue({ status: 'completed', response: {} });

    await pollTaskStatus({ context, taskId: 'task-1', courseId: 'course-v1:Org+Course+Run' });

    expect(mockCallWorkflow).toHaveBeenCalledWith({
      context,
      payload: expect.objectContaining({
        action: WORKFLOW_ACTIONS.GET_RUN_STATUS,
        taskId: 'task-1',
        courseId: 'course-v1:Org+Course+Run',
      }),
    });
  });
});

describe('saveCardStack', () => {
  it('sends SAVE with cardStack in userInput', async () => {
    const cardStack = { cards: [], createdAt: 1000, lastStudiedAt: null };
    mockCallWorkflow.mockResolvedValue({ status: 'completed' });

    await saveCardStack({ context, cardStack });

    expect(mockCallWorkflow).toHaveBeenCalledWith({
      context,
      payload: expect.objectContaining({
        action: WORKFLOW_ACTIONS.SAVE,
        userInput: { cardStack },
      }),
    });
  });
});

describe('getSessionResponse', () => {
  it('sends GET_CURRENT_SESSION_RESPONSE', async () => {
    mockCallWorkflow.mockResolvedValue({ response: {} });

    await getSessionResponse({ context });

    expect(mockCallWorkflow).toHaveBeenCalledWith({
      context,
      payload: expect.objectContaining({
        action: WORKFLOW_ACTIONS.GET_CURRENT_SESSION_RESPONSE,
      }),
    });
  });
});

describe('clearSession', () => {
  it('sends CLEAR_SESSION', async () => {
    mockCallWorkflow.mockResolvedValue({ status: 'session_cleared' });

    await clearSession({ context });

    expect(mockCallWorkflow).toHaveBeenCalledWith({
      context,
      payload: expect.objectContaining({
        action: WORKFLOW_ACTIONS.CLEAR_SESSION,
      }),
    });
  });
});
