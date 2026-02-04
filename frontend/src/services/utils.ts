import { getConfig } from '@edx/frontend-platform';
import { PluginContext } from '../types';

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

    if (pathMatch) return pathMatch[0];
    if (StudioPathMatch) return StudioPathMatch[0];
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
}: PluginContext): Record<string, string> => {
  const resolvedLocationId = locationId || extractLocationIdFromUrl();
  const resolvedCourseId = courseId || extractCourseIdFromUrl();
  const contextData: Record<string, any> = {
    locationId: resolvedLocationId,
    courseId: resolvedCourseId,
  };

  return Object.fromEntries(Object.entries(contextData).filter(([, value]) => value != null)) as Record<string, string>;
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
export const validateEndpoint = (endpoint: string): boolean => {
  try {
    new URL(endpoint, window.location.origin);
    return true;
  } catch (_) {
    return false;
  }
};

/**
 * Get default API endpoint based on environment
 * Uses LMS_BASE_URL or STUDIO_BASE_URL from config
 * @param endpoint - Endpoint type ('workflows' or 'config')
 * @returns Full endpoint URL
 */
export const getDefaultEndpoint = (endpoint = 'workflows'): string => {
  const config = getConfig();
  let baseUrl = config.LMS_BASE_URL as string;
  if (['authoring'].includes(config.APP_ID)) {
    baseUrl = config.STUDIO_BASE_URL as string;
  }
  return `${baseUrl}/openedx-ai-extensions/v1/${endpoint}/`;
};

/**
 * Format error message for user display
 * Maps technical errors to user-friendly messages
 * @param error - Error object or string
 * @returns User-friendly error message
 */
export const formatErrorMessage = (error: Error | any): string => {
  const errorMessage = (error && error.message) ? String(error.message) : String(error || 'Unknown error occurred');
  if (errorMessage.includes('fetch')) return 'Unable to connect to AI service. Please check your connection.';
  if (errorMessage.includes('404')) return 'AI service not available. Please contact support.';
  if (errorMessage.includes('500')) return 'AI service temporarily unavailable. Please try again later.';
  if (errorMessage.includes('timeout')) return 'Request timed out. The AI service may be busy, please try again.';
  return 'Failed to get AI assistance. Please try again.';
};

/**
 * Merge props - config overrides defaults
 */
export const mergeProps = (defaultProps = {}, configProps = {}) => ({
  ...defaultProps,
  ...configProps,
});
