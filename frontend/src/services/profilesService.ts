/**
 * Profiles Service
 * Handles fetching the list of AI Workflow Profiles available for a given course context
 */
import { camelCaseObject } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import { PluginContext, ProfilesListResponse } from '../types';
import { ENDPOINT_TYPES } from '../constants';
import { getDefaultEndpoint } from './utils';

interface FetchProfilesListParams {
  contextData: PluginContext;
  signal?: AbortSignal | null;
}

/**
 * Fetch all AI Workflow Profiles available for the given course context.
 * Omitting uiSlotSelectorId returns profiles for all slots — the intended
 * pattern for the Studio settings panel.
 */
export const fetchProfilesList = async ({
  contextData,
  signal = null,
}: FetchProfilesListParams): Promise<ProfilesListResponse> => {
  const endpoint = getDefaultEndpoint(ENDPOINT_TYPES.LIST_PROFILES);
  const params = new URLSearchParams();
  if (contextData) {
    params.append('context', JSON.stringify(contextData));
  }

  const url = `${endpoint}?${params.toString()}`;
  const client = getAuthenticatedHttpClient();
  const response = await client.get(url, { signal });
  return camelCaseObject(response.data) as ProfilesListResponse;
};
