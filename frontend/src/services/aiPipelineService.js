/**
 * AI Assistant Service Module
 * Handles API calls and context data preparation
 */

import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';

/**
 * Rate limit for rendering streaming chunks (milliseconds)
 * Controls the minimum delay between chunk renders to prevent too-fast rendering
 */
const CHUNK_RATE_LIMIT_MS = 50;

/**
 * Extract course ID from current URL if not provided
 */
const extractCourseIdFromUrl = () => {
  try {
    const pathMatch = window.location.pathname.match(/course\/([^/]+)/);
    return pathMatch ? pathMatch[1] : null;
  } catch {
    return null;
  }
};

/**
 * Extract unit ID from current URL if not provided
 */
const extractLocationIdFromUrl = () => {
  try {
    const pathMatch = window.location.pathname.match(/unit\/([^/]+)/);
    const StudioPathMatch = window.location.pathname.match(/(block-v1:[^/]*type@vertical[^/]*)/);

    if (pathMatch) {
      return pathMatch[0];
    }
    if (StudioPathMatch) {
      return StudioPathMatch[0];
    }
    return null;
  } catch {
    return null;
  }
};

/**
 * Prepare standardized context data for backend API calls.
 *
 * This function generates a context object that the backend expects for Open edX
 * AI workflows. It includes:
 *  - Required unit context (`locationId`)
 *
 * Null or undefined values are automatically removed from the final payload.
 *
 * @param {Object} params
 * @param {string|null} [params.courseId=null] - Course ID (not included directly in context)
 * @param {string|null} [params.locationId=null] - Unit ID (included in context)
 *
 * @returns {Object} A cleaned, standardized context object suitable for backend consumption
 */
export const prepareContextData = ({
  courseId = null, // not included directly in context
  locationId = null, // included in context
} = {}) => {
  const resolvedLocationId = locationId || extractLocationIdFromUrl();
  const resolvedCourseId = courseId || extractCourseIdFromUrl();
  const contextData = {
    // Context that the backend expects
    locationId: resolvedLocationId,
    courseId: resolvedCourseId,

    // Sequence context (if available)
    // sequence: sequence ? {
    //   id: sequence.id,
    //   displayName: sequence.displayName,
    //   })) || [],
    // } : null,

    // Browser context
    // viewport: {
    //   width: window.innerWidth,
    //   height: window.innerHeight,
    // },

    // Language/locale
    // language: navigator.language || 'en',
  };

  // Remove null/undefined values to keep payload clean
  return Object.fromEntries(
    Object.entries(contextData).filter(([, value]) => value != null),
  );
};

/**
 * Generate unique request ID for tracking
 * @returns {string} Unique request identifier
 */
export const generateRequestId = () => {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 15);
  return `ai-request-${timestamp}-${random}`;
};

/**
 * Validate API endpoint configuration
 * @param {string} endpoint - API endpoint URL
 * @returns {boolean} Whether endpoint is valid
 */
export const validateEndpoint = (endpoint) => {
  try {
    // eslint-disable-next-line no-new
    new URL(endpoint, window.location.origin);
    return true;
  } catch {
    return false;
  }
};

/**
 * Get default API endpoint based on environment
 * @param {string} endpoint - Endpoint type: 'workflows' (default) or 'config'
 */
export const getDefaultEndpoint = (endpoint = 'workflows') => {
  const config = getConfig();
  let baseUrl = config.LMS_BASE_URL;
  if (['authoring'].includes(config.APP_ID)) {
    baseUrl = config.STUDIO_BASE_URL;
  }
  return `${baseUrl}/openedx-ai-extensions/v1/${endpoint}/`;
};

/**
 * Make API call to workflow service endpoint
 * Unified function for all workflow API calls.
 *
 * @param {Object} params - Request parameters
 * @param {string} params.endpoint - API endpoint URL or endpoint type ('workflows', 'config')
 * @param {Object} params.payload - Request payload (flexible structure)
 * @param {Object} params.context - Context data (optional, will be added to payload)
 * @param {string} params.action - Action type (optional)
 * @param {string} params.userInput - User input (optional)
 * @param {string} params.workflowType - Workflow type (optional)
 * @param {Object} params.options - Additional options (optional)
 * @param {Function} params.onStreamChunk - Callback for streaming responses.
 * @returns {Promise<Object>} Object containing the full accumulated text and metadata.
 */
export const callWorkflowService = async ({
  endpoint = 'workflows',
  payload = {},
  context = null,
  action = null,
  userInput = null,
  onStreamChunk = null, // Optional callback for streaming text
}) => {
  // Determine the actual endpoint URL
  let apiEndpoint = endpoint.startsWith('http')
    ? endpoint
    : getDefaultEndpoint(endpoint);

  const clientRequestId = payload.requestId || generateRequestId();

  // Build the request payload flexibly
  const requestPayload = {
    timestamp: new Date().toISOString(),
    requestId: clientRequestId,
    ...payload,
  };

  if (context) {
    const params = new URLSearchParams();
    params.append('context', JSON.stringify(context));
    apiEndpoint += `?${params.toString()}`;
  }
  if (action) {
    requestPayload.action = action;
  }
  if (userInput) {
    requestPayload.user_input = userInput;
  }

  try {
    let fullAccumulatedText = '';

    // Always use streaming configuration to capture the response body
    // regardless of whether it is JSON or Text
    const response = await getAuthenticatedHttpClient().post(
      apiEndpoint,
      requestPayload,
      {
        responseType: 'stream',
        adapter: 'fetch', // Required to access the stream reader
      },
    );

    // Detect Content-Type to decide how to process chunks
    const contentType = response.headers['content-type'] || '';
    const isJson = contentType.includes('application/json');

    const reader = response.data.getReader();
    const decoder = new TextDecoder();

    // Rate limiting setup for streaming chunks
    const chunkQueue = [];
    let isProcessingQueue = false;
    let streamingComplete = false;

    // Process chunks from queue at controlled rate
    const processChunkQueue = () => {
      if (chunkQueue.length > 0 && onStreamChunk && typeof onStreamChunk === 'function') {
        const chunk = chunkQueue.shift();
        onStreamChunk(chunk);
      }

      // Continue processing if queue has items or streaming is still ongoing
      if (chunkQueue.length > 0 || !streamingComplete) {
        setTimeout(processChunkQueue, CHUNK_RATE_LIMIT_MS);
      } else {
        isProcessingQueue = false;
      }
    };

    // Consume the stream
    // eslint-disable-next-line no-constant-condition
    while (true) {
      // eslint-disable-next-line no-await-in-loop
      const { done, value } = await reader.read();

      if (done) {
        streamingComplete = true;
        break;
      }

      const chunkText = decoder.decode(value, { stream: true });

      if (chunkText) {
        fullAccumulatedText += chunkText;

        // Only trigger the UI streaming callback if this is effectively a text stream.
        // If it's JSON, we must wait for the full payload to parse it validly.
        if (!isJson && onStreamChunk && typeof onStreamChunk === 'function') {
          chunkQueue.push(chunkText);

          // Start processing queue if not already running
          if (!isProcessingQueue) {
            isProcessingQueue = true;
            processChunkQueue();
          }
        }
      }
    }

    // Wait for queue to finish processing before continuing
    while (chunkQueue.length > 0) {
      // eslint-disable-next-line no-await-in-loop, no-promise-executor-return
      await new Promise(resolve => setTimeout(resolve, CHUNK_RATE_LIMIT_MS));
    }

    // --- PROCESSING COMPLETE ---

    // Scenario A: The backend returned a JSON object (Success or Error)
    if (isJson) {
      try {
        const jsonResult = JSON.parse(fullAccumulatedText);

        // If the backend sent an error status (e.g. 400/500), throw it so the UI handles it as an error
        if (response.status >= 400) {
          throw new Error(jsonResult.error || 'AI Service Error');
        }

        return jsonResult;
      } catch (e) {
        // If we caught an error above, re-throw it.
        // If JSON.parse failed, throw a format error.
        if (e.message !== 'Unexpected end of JSON input') {
          throw e;
        }
        // eslint-disable-next-line no-console
        console.error('Failed to parse AI response:', e);
        throw new Error('Invalid response format from AI service');
      }
    }

    // Scenario B: The backend returned a Streaming Text response
    // If the HTTP status indicates failure but content wasn't JSON, throw error
    if (response.status >= 400) {
      throw new Error(fullAccumulatedText || `Request failed with status ${response.status}`);
    }

    // Return a constructed object matching the shape of a JSON response
    return {
      response: fullAccumulatedText,
      requestId: clientRequestId,
      status: 'success',
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Workflow Service Error:', error);
    throw error;
  }
};

/**
 * Format error message for user display
 * @param {Error} error - Error object
 * @returns {string} User-friendly error message
 */
export const formatErrorMessage = (error) => {
  const errorMessage = error.message || 'Unknown error occurred';

  // Map technical errors to user-friendly messages
  if (errorMessage.includes('fetch')) {
    return 'Unable to connect to AI service. Please check your connection.';
  }

  if (errorMessage.includes('404')) {
    return 'AI service not available. Please contact support.';
  }

  if (errorMessage.includes('500')) {
    return 'AI service temporarily unavailable. Please try again later.';
  }

  if (errorMessage.includes('timeout')) {
    return 'Request timed out. The AI service may be busy, please try again.';
  }

  return 'Failed to get AI assistance. Please try again.';
};
