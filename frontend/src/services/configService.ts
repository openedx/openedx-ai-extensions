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
};

/**
 * Fetch configuration from API
 */
export const fetchConfiguration = async (
  {
    contextData,
    configEndpoint = null,
    signal = null,
  }: FetchConfigurationParams
): Promise<PluginConfiguration | null> => {
  if (!configEndpoint) return null;

  const params = new URLSearchParams();
  if (contextData) {
    params.append('context', JSON.stringify(contextData));
  }

  const url = `${configEndpoint}?${params.toString()}`;
  const client = getAuthenticatedHttpClient();
  const { data } = await client.get(url, {
    signal,
  });

  const componentConfig: Configuration = camelCaseObject(data)

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
