/**
 * Configuration Service
 * Handles fetching runtime configuration for AI assistance components
 */

/**
 * Mock configuration data - simulates API response
 */
const getMockConfig = () => ({
  // The component to render (for now, only GetAIAssistanceButton)
  component: 'GetAIAssistanceButton',

  // Configuration/props to pass to the component
  config: {
    buttonText: 'Ask AI for Help [mock config call]',
    requestMessage: 'Help me understand this topic [mock config call]',
  },

  // Metadata (optional)
  metadata: {
    version: '0.1',
    provider: 'mock',
  },
});

/**
 * Fetch configuration from API (or mock)
 */
export const fetchConfiguration = async ({
  configEndpoint = null,
  courseId = null,
  unitId = null,
  useMock = true,
} = {}) => {
  if (useMock || !configEndpoint) {
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    // eslint-disable-next-line no-console
    console.log('[ConfigService] Using mock configuration');

    return getMockConfig();
  }

  try {
    // eslint-disable-next-line no-console
    console.log('[ConfigService] Fetching from:', configEndpoint);

    const params = new URLSearchParams();
    if (courseId) {
      params.append('course_id', courseId);
    }
    if (unitId) {
      params.append('unit_id', unitId);
    }

    const url = `${configEndpoint}?${params.toString()}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Configuration fetch failed: ${response.status} ${response.statusText}`);
    }

    const config = await response.json();
    return config;
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
