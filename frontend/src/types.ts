export interface PluginContext {
  courseId: string | null;
  locationId: string | null;
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
};

export interface ErrorResponse {
  error: string;
  status: number;
  timestamp: string;
};
