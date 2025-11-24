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
    // Temporary regex to match unit in studio URL structure
    // const pathMatch = window.location.pathname.match(/unit\/([^/]+)/);
    const pathMatch = window.location.pathname.match(/block-v1:[^/]+$/);
    const response = pathMatch ? pathMatch[0] : null;
    return response;
  } catch {
    return null;
  }
};

/**
 * Prepare context data from Open edX learning environment
 * Captures ALL available information without requiring anything specific
 * @param {Object} params - Learning context parameters (all optional)
 * @returns {Object} Formatted context for AI service
 */
export const prepareContextData = ({
  sequence = null,
  courseId = null,
  unitId = null,
  ...extraProps
} = {}) => {
  // Base context that's always available
  const contextData = {
    // Environment info
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    platform: 'openedx-learning-mfe',
    url: window.location.href,
    pathname: window.location.pathname,

    // User info (if available)
    userId: window.user?.id || null,
    username: window.user?.username || null,
    isStaff: window.user?.is_staff || false,

    // Course context (if available)
    courseId: courseId || extractCourseIdFromUrl(),
    unitId: unitId || extractUnitIdFromUrl(),

    // Sequence context (if available)
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

    // Browser context
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },

    // Language/locale
    language: navigator.language || 'en',

    // Any extra props passed in
    ...extraProps,
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
 * Unified function for all workflow API calls
 * @param {Object} params - Request parameters
 * @param {string} params.endpoint - API endpoint URL or endpoint type ('workflows', 'config')
 * @param {Object} params.payload - Request payload (flexible structure)
 * @param {Object} params.context - Context data (optional, will be added to payload)
 * @param {string} params.action - Action type (optional)
 * @param {string} params.userQuery - User query (optional)
 * @param {string} params.workflowType - Workflow type (optional)
 * @param {Object} params.options - Additional options (optional)
 * @returns {Promise<Object>} API response data
 */
export const callWorkflowService = async ({
  endpoint = 'workflows',
  payload = {},
  context = null,
  action = null,
  userQuery = null,
  workflowType = null,
  options = null,
}) => {
  // Determine the actual endpoint URL
  const apiEndpoint = endpoint.startsWith('http')
    ? endpoint
    : getDefaultEndpoint(endpoint);

  // Build the request payload flexibly
  const requestPayload = {
    timestamp: new Date().toISOString(),
    ...payload, // Spread user-provided payload first
  };

  // Add optional fields if provided
  if (context) {
    requestPayload.context = context;
  }
  if (action) {
    requestPayload.action = action;
  }
  if (userQuery) {
    requestPayload.user_query = userQuery;
  }
  if (workflowType) {
    requestPayload.workflow_type = workflowType;
  }
  if (options) {
    requestPayload.options = options;
  }

  try {
    // Use Open edX authenticated HTTP client
    const { data } = await getAuthenticatedHttpClient()
      .post(apiEndpoint, requestPayload);

    if (!data) {
      throw new Error('Empty response from workflow service');
    }

    return data;
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
