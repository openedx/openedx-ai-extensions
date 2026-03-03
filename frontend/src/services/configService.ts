/**
 * Configuration Service
 * Handles fetching runtime configuration for AI assistance components
 */
import { camelCaseObject } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import { PluginConfiguration, PluginContext } from '../types';
import { ProfileStatus } from '../constants';

interface FetchConfigurationParams {
  contextData: PluginContext;
  configEndpoint: string | null;
  signal?: AbortSignal | null;
}

interface Configuration {
  timestamp: string;
  status?: string;
  courseId?: string | null;
  uiComponents?: PluginConfiguration;
}

/**
 * Fetch configuration from API
 */
export const fetchConfiguration = async (
  {
    contextData,
    configEndpoint = null,
    signal = null,
  }: FetchConfigurationParams,
): Promise<PluginConfiguration | null> => {
  if (!configEndpoint) { return null; }

  const params = new URLSearchParams();
  if (contextData) {
    params.append('context', JSON.stringify(contextData));
  }

  const url = `${configEndpoint}?${params.toString()}`;
  const client = getAuthenticatedHttpClient();

  let response;
  try {
    response = await client.get(url, { signal });
  } catch (err: any) {
    // 404 means no scope is configured for this widget — silently hide it
    if (err?.response?.status === 404 || err?.customAttributes?.httpErrorStatus === 404) {
      return null;
    }
    throw err;
  }

  const { data } = response;
  const componentConfig: Configuration = camelCaseObject(data);

  // Handle no_config status - return null to hide components
  if (componentConfig && data.status === ProfileStatus.NO_CONFIG) {
    return null;
  }

  // Extract config from nested response structure
  if (componentConfig.uiComponents) {
    return componentConfig.uiComponents;
  }

  // Fallback: return data as-is if structure is different
  return data;
};
