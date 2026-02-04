export const ProfileStatus = {
  NO_CONFIG: 'no_config',
};

/**
 * Rate limit for rendering streaming chunks (milliseconds)
 * Controls the minimum delay between chunk renders to prevent too-fast rendering
 */
export const DEFAULT_CHUNK_RATE_LIMIT_MS = 50;

export const ENDPOINT_TYPES = {
  WORKFLOWS: 'workflows',
  PROFILE: 'profile',
} as const;

export type EndpointType = typeof ENDPOINT_TYPES[keyof typeof ENDPOINT_TYPES];

export const WORKFLOW_ACTIONS = {
  RUN: 'run',
  SIMPLE_BUTTON_ASSISTANCE: 'simple_button_assistance',
  GET_CURRENT_SESSION_RESPONSE: 'get_current_session_response',
  GET_RUN_STATUS: 'get_run_status',
  CANCEL_RUN: 'cancel_run',
  CLEAR_SESSION: 'clear_session',
  LAZY_LOAD_CHAT_HISTORY: 'lazy_load_chat_history',
} as const;

export type WorkflowActionType = typeof WORKFLOW_ACTIONS[keyof typeof WORKFLOW_ACTIONS];
