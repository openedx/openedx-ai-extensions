import { mergeConfig } from '@edx/frontend-platform';
import { getAuthenticatedHttpClient } from '@edx/frontend-platform/auth';
import { waitFor } from '@testing-library/react';
import { renderWrapper as render } from './setupTest';
import ConfigurableAIAssistance from './ConfigurableAIAssistance';

jest.mock('@edx/frontend-platform/auth', () => ({
  getAuthenticatedHttpClient: jest.fn(),
}));

jest.mock('@edx/frontend-platform/logging', () => ({
  logError: jest.fn(),
}));

/**
 * `react-markdown` ships ESM only, which jest does not transform out of the
 * box, and it reaches this file through the response components. Nothing here
 * renders markdown, so a stub keeps the real component importable.
 */
jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }: any) => <div data-testid="markdown">{children}</div>,
}));

const mockGet = jest.fn();

/** A profile the component can actually render, for the contrast cases. */
const workingProfile = {
  data: {
    ui_components: {
      request: { component: 'AIRequestComponent' },
      response: { component: 'AIResponseComponent' },
    },
  },
};

/**
 * `onNoConfig` is what lets a host tell "nothing is configured here" apart from
 * "still loading" and "the request failed". Without it the component renders
 * nothing in the first case and the host cannot see the difference, which is
 * how the sidebar page ended up opening blank.
 */
describe('ConfigurableAIAssistance config callbacks', () => {
  const callbacks = () => ({
    onConfigLoad: jest.fn(),
    onNoConfig: jest.fn(),
    onConfigError: jest.fn(),
  });

  beforeEach(() => {
    jest.clearAllMocks();
    (getAuthenticatedHttpClient as jest.Mock).mockReturnValue({ get: mockGet });
    mergeConfig({ LMS_BASE_URL: 'http://localhost:18000', STUDIO_BASE_URL: 'http://localhost:18010' });
  });

  it('reports no config when the profile endpoint 404s', async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } });
    const handlers = callbacks();

    render(<ConfigurableAIAssistance uiSlotSelectorId="quiz-generator" {...handlers} />);

    await waitFor(() => expect(handlers.onNoConfig).toHaveBeenCalledTimes(1));
    expect(handlers.onConfigLoad).not.toHaveBeenCalled();
    expect(handlers.onConfigError).not.toHaveBeenCalled();
  });

  it('reports no config on a no_config response', async () => {
    mockGet.mockResolvedValue({ data: { status: 'no_config' } });
    const handlers = callbacks();

    render(<ConfigurableAIAssistance uiSlotSelectorId="quiz-generator" {...handlers} />);

    await waitFor(() => expect(handlers.onNoConfig).toHaveBeenCalledTimes(1));
    expect(handlers.onConfigLoad).not.toHaveBeenCalled();
    expect(handlers.onConfigError).not.toHaveBeenCalled();
  });

  it('reports a configuration instead when one comes back', async () => {
    mockGet.mockResolvedValue(workingProfile);
    const handlers = callbacks();

    render(<ConfigurableAIAssistance uiSlotSelectorId="quiz-generator" {...handlers} />);

    await waitFor(() => expect(handlers.onConfigLoad).toHaveBeenCalledTimes(1));
    expect(handlers.onNoConfig).not.toHaveBeenCalled();
  });

  it('reports an error, not a missing config, when the request fails', async () => {
    mockGet.mockRejectedValue({ response: { status: 500 } });
    const handlers = callbacks();

    render(<ConfigurableAIAssistance uiSlotSelectorId="quiz-generator" {...handlers} />);

    await waitFor(() => expect(handlers.onConfigError).toHaveBeenCalledTimes(1));
    expect(handlers.onNoConfig).not.toHaveBeenCalled();
    expect(handlers.onConfigLoad).not.toHaveBeenCalled();
  });

  it('stays silent when the host passes no callbacks', async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } });

    const { container } = render(<ConfigurableAIAssistance uiSlotSelectorId="quiz-generator" />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
