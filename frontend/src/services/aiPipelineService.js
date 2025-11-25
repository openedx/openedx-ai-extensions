/**
 * AI Assistant Service Module
 * Handles API calls and context data preparation
 */

import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';

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
const extractUnitIdFromUrl = () => {
  try {
    const pathMatch = window.location.pathname.match(/unit\/([^/]+)/);
    return pathMatch ? pathMatch[1] : null;
  } catch {
    return null;
  }
};

/**
 * Prepare standardized context data (Backend requires context.unitId + extra info)
 */
export const prepareContextData = ({
  sequence = null,
  // eslint-disable-next-line no-unused-vars
  courseId = null, // not included directly in context
  unitId = null, // included in context
  ...extraProps
} = {}) => {
  const resolvedUnitId = unitId || extractUnitIdFromUrl();

  const contextData = {
    // Context that the backend expects
    unitId: resolvedUnitId,

    // Environment info
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    platform: 'openedx-learning-mfe',
    url: window.location.href,
    pathname: window.location.pathname,

    // User info
    userId: window.user?.id || null,
    username: window.user?.username || null,
    isStaff: window.user?.is_staff || false,

    // Sequence details
    sequence: sequence ? {
      id: sequence.id,
      displayName: sequence.displayName,
      blockCount: sequence.unitBlocks?.length || 0,
      blockTypes: sequence.unitBlocks?.map(block => block.type) || [],
      blocks: sequence.unitBlocks?.map(block => ({
        id: block.id,
        type: block.type,
        displayName: block.displayName,
        // Capture any additional block properties
        ...block,
      })) || [],
    } : null,

    // Browser viewport
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },

    // Language
    language: navigator.language || 'en',

    ...extraProps, // additional UI-provided context
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
 * Main AI Workflow API call
 */
export const callAIService = async ({
  contextData = {},
  userQuery = '',
  action = 'simple_button_assistance',
  courseId = '',
  apiEndpoint = '',
  requestId = null,
  options = {},
}) => {
  const resolvedCourseId = courseId || extractCourseIdFromUrl();

  const requestPayload = {
    requestId: requestId || generateRequestId(),
    action,
    courseId: resolvedCourseId,
    timestamp: new Date().toISOString(),

    // Standardized field names (backend uses user_input + context)
    user_input: { query: userQuery },
    context: contextData,

    options: {
      responseFormat: 'text',
      maxTokens: 1000,
      temperature: 0.7,
      ...options,
    },

    // Include any additional data
    metadata: {
      source: 'openedx-ai-extensions',
      version: '1.0.0',
      mfe: 'learning',
    },
  };

  try {
    // Use Open edX authenticated HTTP client
    // This automatically handles JWT cookies and CSRF tokens
    const { data } = await getAuthenticatedHttpClient()
      .post(apiEndpoint, requestPayload);

    // Very flexible response validation - accept any structure
    if (!data) {
      throw new Error('Empty response from AI service');
    }

    return data;
  } catch (error) {
    // Log error for debugging
    // eslint-disable-next-line no-console
    console.error('AI Service Error:', error);

    // Re-throw the original error
    throw error;
  }
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
  const lmsBaseUrl = config.LMS_BASE_URL;
  return `${lmsBaseUrl}/openedx-ai-extensions/v1/${endpoint}/`;
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
    return 'Request timed out. Please try again.';
  }

  return 'Failed to get AI assistance. Please try again.';
};
