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
} = {}) => {
  // eslint-disable-next-line no-console
  console.log('[ConfigService]', contextData, configEndpoint);

  try {
    // eslint-disable-next-line no-console
    console.log('[ConfigService] Fetching from:', configEndpoint, 'with context:', contextData);

    const params = new URLSearchParams();
    if (contextData) {
      params.append('context', JSON.stringify(contextData));
    }

    const url = `${configEndpoint}?${params.toString()}`;
    const client = getAuthenticatedHttpClient();
    const { data } = await client.get(url);

    // Extract config from nested response structure
    if (data.ui_components && data.ui_components.request) {
      return data.ui_components.request;
    }

    // Fallback: return data as-is if structure is different
    return data;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('[ConfigService] Error fetching configuration:', error);
    throw error;
  }
};

/**
 * Merge props - config overrides defaults
 */
export const mergeProps = (defaultProps = {}, configProps = {}) => ({
  ...defaultProps,
  ...configProps,
});
