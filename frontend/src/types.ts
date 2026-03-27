export interface PluginContext {
  courseId?: string | null;
  locationId?: string | null;
  /**
   * Discriminator for multi-scope setups.
   * Must match the ui_slot_selector_id configured in the backend AIWorkflowScope admin.
   */
  uiSlotSelectorId?: string | null;
}

export interface UiComponent {
  component: string;
  config: Record<string, string>;
}

export interface PluginConfiguration {
  request: UiComponent;
  response: UiComponent;
  metadata?: {
    [key: string]: any;
  };
}

export interface ErrorResponse {
  error: string;
  status: number;
  timestamp: string;
}

type MessageType = 'user' | 'ai' | 'error';

interface Message {
  content: string;
  timestamp: string;
}

export interface AIChatMessage extends Message {
  type: MessageType;
  originalIndex?: number;
}

export interface AIModelResponse extends Message {
  role: 'user' | 'assistant';
}

export interface PromptTemplate {
  id: string;
  slug: string;
  body: string;
  createdAt: string;
  updatedAt: string;
}

export interface AIWorkflowScope {
  id: string;
  courseId: string | null;
  serviceVariant: string | null;
  enabled: boolean;
  uiSlotSelectorId: string;
  locationRegex: string | null;
  specificityIndex: number;
}

export interface AIWorkflowProfile {
  id: string;
  slug: string;
  description: string | null;
  effectiveConfig: Record<string, any>;
  scopes: AIWorkflowScope[];
}

export interface ProfilesListResponse {
  profiles: AIWorkflowProfile[];
  count: number;
  timestamp: string;
}
