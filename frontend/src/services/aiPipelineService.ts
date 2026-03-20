/**
 * AI Assistant Service Module
 * Main workflow service for streaming API calls with timeout support
 */
import { camelCaseObject, snakeCaseObject } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import { logError } from '@edx/frontend-platform/logging';
import {
  generateRequestId,
  getDefaultEndpoint,
} from './utils';
import { PluginContext } from '../types';
import {
  DEFAULT_CHUNK_RATE_LIMIT_MS, ENDPOINT_TYPES, EndpointType, WorkflowActionType,
} from '../constants';

interface Payload {
  action: WorkflowActionType;
  timestamp?: string;
  requestId?: string;
  userInput?: string | Record<string, any>;
  [key: string]: any;
}

export interface WorkflowServiceParams {
  payload: Payload;
  endpoint?: EndpointType;
  context?: PluginContext | null;
  userInput?: string | null;
  workflowType?: string | null;
  options?: { timeout?: number; chunkRateMs?: number } & Record<string, any>;
  onStreamChunk?: ((chunk: string) => void) | null;
}

export interface WorkflowServiceResult {
  response?: string;
  requestId?: string;
  status?: string;
  timestamp?: string;
  [k: string]: any;
}

export const callWorkflowService = async ({
  endpoint = ENDPOINT_TYPES.WORKFLOWS,
  payload,
  context = null,
  userInput = null,
  options = {},
  onStreamChunk = null,
}: WorkflowServiceParams): Promise<WorkflowServiceResult> => {
  const chunkRate = typeof options.chunkRateMs === 'number' ? options.chunkRateMs : DEFAULT_CHUNK_RATE_LIMIT_MS;

  let apiEndpoint = endpoint?.startsWith('http') ? endpoint : getDefaultEndpoint(endpoint);

  const clientRequestId: string = payload.requestId ?? generateRequestId();

  const requestPayload: Payload = {
    ...payload,
    timestamp: payload.timestamp ?? new Date().toISOString(),
    requestId: clientRequestId,
  };

  if (context) {
    const params = new URLSearchParams();
    params.append('context', JSON.stringify(context));
    apiEndpoint += `?${params.toString()}`;
  }

  if (userInput) { requestPayload.userInput = userInput; }

  const controller = new AbortController();
  let timeoutId: number | undefined;
  if (options && typeof options.timeout === 'number' && options.timeout > 0) {
    timeoutId = window.setTimeout(() => controller.abort(), options.timeout);
  }

  try {
    let fullAccumulatedText = '';

    const response = await getAuthenticatedHttpClient().post(apiEndpoint, snakeCaseObject(requestPayload), {
      responseType: 'stream',
      adapter: 'fetch',
      signal: controller.signal as AbortSignal,
      validateStatus: () => true,
    } as any);

    const contentType = (response.headers && (response.headers['content-type'] || response.headers['Content-Type'])) || '';
    const isJson = String(contentType).toLowerCase().includes('application/json');

    const reader = response.data.getReader();
    const decoder = new TextDecoder();

    const chunkQueue: string[] = [];
    let isProcessingQueue = false;
    let streamingComplete = false;

    const processChunkQueue = () => {
      if (chunkQueue.length > 0 && onStreamChunk && typeof onStreamChunk === 'function') {
        const chunk = chunkQueue.shift() as string;
        onStreamChunk(chunk);
      }
      if (chunkQueue.length > 0 || !streamingComplete) {
        setTimeout(processChunkQueue, chunkRate);
      } else {
        isProcessingQueue = false;
      }
    };

    // Stream consume loop
    // eslint-disable-next-line no-constant-condition
    while (true) {
      // eslint-disable-next-line no-await-in-loop
      const { done, value } = await reader.read();
      if (done) { streamingComplete = true; break; }
      const chunkText = decoder.decode(value, { stream: true });
      if (chunkText) {
        const previousAccumulatedText = fullAccumulatedText;
        fullAccumulatedText += chunkText;

        // Check for mid-stream error marker
        const markerStart = fullAccumulatedText.indexOf('||{"error_in_stream":');
        if (markerStart !== -1) {
          // Push only the safe part (before the marker) to the queue
          const markerStartInChunk = markerStart - previousAccumulatedText.length;
          if (markerStartInChunk > 0) {
            const safeChunk = chunkText.substring(0, markerStartInChunk);
            if (!isJson && onStreamChunk && typeof onStreamChunk === 'function') {
              chunkQueue.push(safeChunk);
            }
          }

          const markerEnd = fullAccumulatedText.indexOf('||', markerStart + 2);
          if (markerEnd !== -1) {
            const markerJson = fullAccumulatedText.substring(markerStart + 2, markerEnd);
            try {
              const errorObj = JSON.parse(markerJson);
              const error = new Error(errorObj.message || 'Streaming error');
              (error as any).code = errorObj.code || 'streaming_failed';
              (error as any).isStreamError = true;
              // Clear queue and stop further chunk processing
              chunkQueue.length = 0;
              streamingComplete = true;
              throw error;
            } catch (e: any) {
              if (e.isStreamError) { throw e; }
              // JSON parse failed or other error
            }
          }
          // Marker found but not complete - don't push the rest of this chunk
        } else if (!isJson && onStreamChunk && typeof onStreamChunk === 'function') {
          chunkQueue.push(chunkText);
          if (!isProcessingQueue) {
            isProcessingQueue = true;
            processChunkQueue();
          }
        }
      }
    }

    // Wait for queue to empty
    while (chunkQueue.length > 0) {
      // eslint-disable-next-line no-await-in-loop
      await new Promise<void>((resolve) => { setTimeout(resolve, chunkRate); });
    }

    // PROCESSING COMPLETE
    if (isJson) {
      try {
        const jsonResult = JSON.parse(fullAccumulatedText);
        if (response.status >= 400 || jsonResult.status === 'error') {
          const error = new Error(jsonResult.error?.message || 'AI Service Error');
          (error as any).code = jsonResult.error?.code;
          throw error;
        }
        return camelCaseObject(jsonResult) as WorkflowServiceResult;
      } catch (e: any) {
        if (e && e.code) { throw e; }
        if (e && e.message && e.message !== 'Unexpected end of JSON input') { throw e; }
        // parse failed
        logError('Failed to parse AI response:', e);
        throw new Error('Invalid response format from AI service');
      }
    }

    if (response.status >= 400) {
      throw new Error(fullAccumulatedText || `Request failed with status ${response.status}`);
    }

    return {
      response: fullAccumulatedText,
      requestId: clientRequestId,
      status: 'success',
      timestamp: new Date().toISOString(),
    } as WorkflowServiceResult;
  } catch (error) {
    logError('Workflow Service Error:', error);
    throw error;
  } finally {
    if (timeoutId) { window.clearTimeout(timeoutId); }
  }
};
