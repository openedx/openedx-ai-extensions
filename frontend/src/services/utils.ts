import { getConfig } from '@edx/frontend-platform';
import { PluginContext } from '../types';
import { ENDPOINT_TYPES, EndpointType } from '../constants';

/**
 * Extract course ID from current URL
 * @returns Course ID string or null if not found
 */
export const extractCourseIdFromUrl = (): string | null => {
  try {
    const pathMatch = window.location.pathname.match(/course\/([^/]+)/);
    return pathMatch ? pathMatch[1] : null;
  } catch {
    return null;
  }
};

/**
 * Extract unit/location ID from current URL
 * @returns Location ID string or null if not found
 */
export const extractLocationIdFromUrl = (): string | null => {
  try {
    const pathMatch = window.location.pathname.match(/unit\/([^/]+)/);
    const StudioPathMatch = window.location.pathname.match(/(block-v1:[^/]*type@vertical[^/]*)/);

    if (pathMatch) { return pathMatch[0]; }
    if (StudioPathMatch) { return StudioPathMatch[0]; }
    return null;
  } catch {
    return null;
  }
};

/**
 * Prepare standardized context data for backend API calls
 * Extracts courseId and locationId from params or URL
 * @param params - Optional courseId and locationId overrides
 * @returns Cleaned context object with only non-null values
 */
export const prepareContextData = ({
  courseId = null,
  locationId = null,
  uiSlotSelectorId = null,
}: PluginContext): PluginContext => {
  const resolvedLocationId = locationId || extractLocationIdFromUrl();
  const resolvedCourseId = courseId || extractCourseIdFromUrl();
  const contextData: PluginContext = {
    locationId: resolvedLocationId,
    courseId: resolvedCourseId,
    uiSlotSelectorId: uiSlotSelectorId || null,
  };

  return Object.fromEntries(Object.entries(contextData).filter(([, value]) => value != null)) as PluginContext;
};

/**
 * Generate unique request ID for tracking
 * @returns Unique request identifier combining timestamp and random string
 */
export const generateRequestId = (): string => {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 15);
  return `ai-request-${timestamp}-${random}`;
};

/**
 * Validate API endpoint URL format
 * @param endpoint - Endpoint URL to validate
 * @returns True if endpoint is valid, false otherwise
 */
export const validateEndpoint = (endpoint: EndpointType = ENDPOINT_TYPES.WORKFLOWS): boolean => {
  try {
    const url = new URL(endpoint, window.location.origin);
    return !!url;
  } catch (_) {
    return false;
  }
};

/**
 * Get default API endpoint based on environment
 * Uses LMS_BASE_URL or STUDIO_BASE_URL from config
 * @param endpoint - Endpoint type ('workflows' or 'profile')
 * @returns Full endpoint URL
 */

export const getDefaultEndpoint = (endpoint: EndpointType = ENDPOINT_TYPES.WORKFLOWS): string => {
  const config = getConfig();
  let baseUrl = config.LMS_BASE_URL as string;
  if (['authoring'].includes(config.APP_ID)) {
    baseUrl = config.STUDIO_BASE_URL as string;
  }
  return `${baseUrl}/openedx-ai-extensions/v1/${endpoint}/`;
};

/**
 * User-friendly error messages keyed by backend error codes.
 * This can be easily extended or moved to a configuration file.
 */
const ERROR_MESSAGES: Record<string, string> = {
  invalid_api_key: 'The AI service is currently unavailable due to a configuration error. Please contact support.',
  rate_limit_exceeded: 'The AI service is currently busy. Please try again in a few moments.',
  service_unavailable: 'The AI service is temporarily unavailable. Please try again later.',
  context_window_exceeded: 'The text is too long for the AI to process. Please try with a shorter selection.',
  validation_error: 'There was a problem with the request. Please check your input and try again.',
  streaming_failed: 'The AI service encountered an error while generating the response. Please try again.',
  internal_error: 'An unexpected error occurred. Please try again later.',
};

/**
 * Format error message for user display.
 * Prioritizes localized messages from ERROR_MESSAGES dictionary.
 *
 * @param error - Error object containing code and message properties
 * @returns User-friendly error message
 */
export const formatErrorMessage = (error: any): string => {
  // 1. Check for the new error contract structure
  const errorCode = error?.errorCode || error?.code;
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode];
  }

  // 2. Fall back to the message provided by the backend (sanitized for the user)
  if (error?.message && typeof error.message === 'string') {
    // Basic sanitization: don't show raw JSON or technical stack traces
    if (!error.message.includes('{') && !error.message.includes('Traceback')) {
      return error.message;
    }
  }

  // 3. Generic fallback
  return 'Failed to get AI assistance. Please try again later.';
};

/**
 * Merge props - config overrides defaults
 */
export const mergeProps = (defaultProps = {}, configProps = {}) => ({
  ...defaultProps,
  ...configProps,
});
