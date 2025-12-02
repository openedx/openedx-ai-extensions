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
    const StudioPathMatch = window.location.pathname.match(/block-v1:[^/]+$/);

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
 *  - Required unit context (`unitId`)
 *  - User information (ID, username, staff status)
 *  - Sequence/block metadata if a sequence is provided
 *  - Browser environment info (viewport, URL, platform, language)
 *  - Additional properties passed via `extraProps`
 *
 * Null or undefined values are automatically removed from the final payload.
 *
 * @param {Object} params
 * @param {Object|null} [params.sequence=null] - Optional sequence object containing units/blocks
 * @param {string|null} [params.courseId=null] - Course ID (not included directly in context)
 * @param {string|null} [params.unitId=null] - Unit ID (included in context)
 * @param {Object} [params.extraProps={}] - Any additional properties to merge into context
 *
 * @returns {Object} A cleaned, standardized context object suitable for backend consumption
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

    // User info (if available)
    userId: window.user?.id || null,
    username: window.user?.username || null,
    isStaff: window.user?.is_staff || false,

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

    // Browser viewport context
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
 * @param {string} params.userInput - User input (optional)
 * @param {string} params.workflowType - Workflow type (optional)
 * @param {Object} params.options - Additional options (optional)
 * @returns {Promise<Object>} API response data
 */
export const callWorkflowService = async ({
  endpoint = 'workflows',
  payload = {},
  context = null,
  action = null,
  userInput = null,
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
  if (userInput) {
    requestPayload.user_input = userInput;
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
