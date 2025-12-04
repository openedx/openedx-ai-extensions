/**
 * Configuration Service
 * Handles fetching runtime configuration for AI assistance components
 */

import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';

/**
 * Fetch configuration from API
 */
export const fetchConfiguration = async ({
  configEndpoint = null,
  contextData = null,
  signal = null,
} = {}) => {
  const params = new URLSearchParams();
  if (contextData) {
    params.append('context', JSON.stringify(contextData));
  }

  const url = `${configEndpoint}?${params.toString()}`;
  const client = getAuthenticatedHttpClient();
  const { data } = await client.get(url, {
    signal,
  });

  // Handle no_config status - return null to hide components
  if (data.status === 'no_config') {
    return null;
  }

  // Extract config from nested response structure
  if (data.ui_components) {
    // Return both request and response configurations
    return {
      request: data.ui_components.request || null,
      response: data.ui_components.response || null,
      metadata: data.ui_components.metadata || null,
    };
  }

  // Fallback: return data as-is if structure is different
  return data;
};

/**
 * Merge props - config overrides defaults
 */
export const mergeProps = (defaultProps = {}, configProps = {}) => ({
  ...defaultProps,
  ...configProps,
});
