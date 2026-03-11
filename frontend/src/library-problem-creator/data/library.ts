import { getConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';

export interface Library {
  id: string;
  title: string;
}

/**
 * Fetches the list of content libraries available in Studio.
 * Returns the raw array; state management is handled by the caller.
 */
export async function fetchLibrariesApi(): Promise<Library[]> {
  const config = getConfig();
  const endpoint = `${config.STUDIO_BASE_URL}/api/libraries/v2/?pagination=false&order=title`;
  const { data } = await getAuthenticatedHttpClient().get(endpoint);
  return Array.isArray(data) ? data : (data?.results ?? []);
}
