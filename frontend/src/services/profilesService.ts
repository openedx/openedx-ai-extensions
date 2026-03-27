/**
 * Profiles Service
 * Handles fetching the list of AI Workflow Profiles available for a given course context,
 * and fetching/saving individual prompt templates.
 */
import { camelCaseObject } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import { PluginContext, ProfilesListResponse, PromptTemplate } from '../types';
import { ENDPOINT_TYPES } from '../constants';
import { getDefaultEndpoint } from './utils';

interface FetchProfilesListParams {
  contextData: PluginContext;
  signal?: AbortSignal | null;
}

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
  const response = await getAuthenticatedHttpClient().get(url, { signal });
  return camelCaseObject(response.data) as ProfilesListResponse;
};

const getPromptUrl = (identifier: string): string => {
  const base = getDefaultEndpoint('prompts' as any).replace(/\/$/, '');
  return `${base}/${identifier}/`;
};

export const fetchPromptTemplate = async ({
  identifier,
  signal = null,
}: {
  identifier: string;
  signal?: AbortSignal | null;
}): Promise<PromptTemplate> => {
  const response = await getAuthenticatedHttpClient().get(getPromptUrl(identifier), { signal });
  return camelCaseObject(response.data) as PromptTemplate;
};

export const savePromptTemplate = async ({
  identifier,
  body,
}: {
  identifier: string;
  body: string;
}): Promise<PromptTemplate> => {
  const response = await getAuthenticatedHttpClient().patch(getPromptUrl(identifier), { body });
  return camelCaseObject(response.data) as PromptTemplate;
};
