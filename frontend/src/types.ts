export interface PluginContext {
  courseId?: string | null;
  locationId?: string | null;
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
