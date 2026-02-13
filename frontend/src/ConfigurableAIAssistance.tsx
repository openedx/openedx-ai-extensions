import React, {
  useState, useEffect, useRef, useCallback,
} from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { logError } from '@edx/frontend-platform/logging';
import { Spinner, Alert } from '@openedx/paragon';
import { Info } from '@openedx/paragon/icons';

// Import services
import {
  fetchConfiguration,
  getDefaultEndpoint,
  mergeProps,
  prepareContextData,
  callWorkflowService,
  formatErrorMessage,
} from './services';

// Import available components
import {
  AIRequestComponent,
  AIResponseComponent,
  AISidebarResponse,
  AIEducatorLibraryAssistComponent,
  AIEducatorLibraryResponseComponent,
} from './components';
import { PluginConfiguration } from './types';
import { WORKFLOW_ACTIONS } from './constants';

import messages from './messages';

/**
 * Component Registry
 * Maps component names from config to actual React components
 */
const COMPONENT_REGISTRY = {
  AIRequestComponent,
  AIResponseComponent,
  AISidebarResponse,
  AIEducatorLibraryAssistComponent,
  AIEducatorLibraryResponseComponent,
  // Future components can be added here
};

/**
 * Configurable AI Assistance Wrapper Component
 * Fetches runtime configuration from an API and dynamically renders
 * AIRequestComponent and AIResponseComponent with configuration.
 * Manages state and orchestrates the AI interaction flow.
 */

interface ConfigurableAIAssistanceProps {
  fallbackConfig?: PluginConfiguration | null;
  onConfigLoad?: (config: PluginConfiguration) => void;
  onConfigError?: (error) => void;
}

const ConfigurableAIAssistance = ({
  fallbackConfig = null,
  onConfigLoad,
  onConfigError,
  ...additionalProps
}: ConfigurableAIAssistanceProps) => {
  const intl = useIntl();
  // Configuration state
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [configError, setConfigError] = useState<null | string>(null);
  const [config, setConfig] = useState<PluginConfiguration | null>(null);

  // AI interaction state
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState('');
  const [error, setError] = useState('');
  const [hasAsked, setHasAsked] = useState(false);

  const configEndpoint = getDefaultEndpoint('profile');
  const requestIdRef = useRef(0);

  // Load configuration on mount
  useEffect(() => {
    const abortController = new AbortController();
    const currentRequestId = ++requestIdRef.current;

    const loadConfiguration = async () => {
      setIsLoadingConfig(true);
      setConfigError(null);

      const contextData = prepareContextData({
        ...additionalProps,
      });

      try {
        const fetchedConfig = await fetchConfiguration({
          configEndpoint,
          contextData,
          signal: abortController.signal,
        });

        // Only update state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          setConfig(fetchedConfig);

          if (onConfigLoad && fetchedConfig) {
            onConfigLoad(fetchedConfig);
          }
        }
      } catch (err) {
        // Type guard for error
        const configErr = err instanceof Error ? err : new Error(String(err));

        // Ignore aborted requests
        if (configErr.name === 'AbortError' || configErr.message?.includes('aborted')) {
          return;
        }

        // Only update state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          logError('[ConfigurableAIAssistance] Configuration error:', configErr);

          setConfigError(configErr.message);

          if (fallbackConfig) {
            setConfig(fallbackConfig);
          }

          if (onConfigError) {
            onConfigError(err);
          }
        }
      } finally {
        // Only update loading state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          setIsLoadingConfig(false);
        }
      }
    };

    loadConfiguration();

    return () => {
      abortController.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configEndpoint]);

  /**
   * Handle AI assistant request
   */
  const handleAskAI = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setResponse('');

    try {
      // Prepare context data
      const contextData = prepareContextData({
        ...additionalProps,
      });

      let buffer = '';
      // Make API call
      const data = await callWorkflowService({
        context: contextData,
        payload: {
          action: WORKFLOW_ACTIONS.RUN,
          requestId: `ai-request-${Date.now()}`,
        },
        onStreamChunk: (chunk) => {
          setIsLoading(false);
          setHasAsked(true);
          buffer += chunk;
          setResponse(buffer);
        },
      });
      // Handle response
      if (data.response) {
        setResponse(data.response);
        setHasAsked(true);
      } else if (data.message) {
        setResponse(data.message);
        setHasAsked(true);
      } else if (data.content) {
        setResponse(data.content);
        setHasAsked(true);
      } else if (data.result) {
        setResponse(data.result);
        setHasAsked(true);
      } else if (data.error) {
        throw new Error(data.error);
      } else {
        setResponse(JSON.stringify(data, null, 2));
        setHasAsked(true);
      }

      setHasAsked(true);
    } catch (err) {
      logError('[ConfigurableAIAssistance] AI Assistant Error:', err);
      const userFriendlyError = formatErrorMessage(err);
      setError(userFriendlyError);
    } finally {
      setIsLoading(false);
    }
  }, [additionalProps]);

  /**
   * Reset component state for new request
   */
  const handleReset = useCallback(() => {
    setResponse('');
    setError('');
    setHasAsked(false);
  }, []);

  /**
   * Clear error state but keep button available
   */
  const handleClearError = useCallback((errorMessage = '') => {
    setError(errorMessage);
  }, []);

  // Show loading spinner while loading configuration
  if (isLoadingConfig) {
    return (
      <div className="d-flex align-items-center justify-content-center p-3">
        <Spinner animation="border" size="sm" role="status" />
      </div>
    );
  }

  // Show error if configuration failed and no fallback
  if (configError && !fallbackConfig) {
    return (
      <Alert variant="danger" icon={Info}>
        <Alert.Heading>{intl.formatMessage(messages['ai.extensions.config.alert.heading'])}</Alert.Heading>
        <p>{intl.formatMessage(messages['ai.extensions.config.alert.message'], { error: configError })}</p>
      </Alert>
    );
  }

  // Don't render anything if no config is available (silently hide)
  if (!config) {
    return null;
  }

  // Render configured components
  if (config) {
    // Both request and response configs are required
    const requestConfig = config.request;
    const responseConfig = config.response;

    // Validate request config
    if (!requestConfig) {
      return (
        <Alert variant="danger">
          <Alert.Heading>{intl.formatMessage(messages['ai.extensions.config.invalid.heading'])}</Alert.Heading>
          <p>{intl.formatMessage(messages['ai.extensions.config.missing.request'])}</p>
        </Alert>
      );
    }

    // Validate response config
    if (!responseConfig) {
      return (
        <Alert variant="danger">
          <Alert.Heading>{intl.formatMessage(messages['ai.extensions.config.invalid.heading'])}</Alert.Heading>
          <p>{intl.formatMessage(messages['ai.extensions.config.missing.response'])}</p>
        </Alert>
      );
    }

    // Get request component
    const { component: requestComponentName, config: requestComponentConfig = {} } = requestConfig;
    const RequestComponent = COMPONENT_REGISTRY[requestComponentName];

    if (!RequestComponent) {
      return (
        <Alert variant="danger">
          <Alert.Heading>{intl.formatMessage(messages['ai.extensions.config.unknown.heading'])}</Alert.Heading>
          <p>{intl.formatMessage(messages['ai.extensions.config.unknown.request'], { componentName: requestComponentName })}</p>
          <p className="mb-0 text-muted small">
            {intl.formatMessage(messages['ai.extensions.config.available.components'], { components: Object.keys(COMPONENT_REGISTRY).join(', ') })}
          </p>
        </Alert>
      );
    }

    // Get response component
    const { component: responseComponentName, config: responseComponentConfig = {} } = responseConfig;
    const ResponseComponent = COMPONENT_REGISTRY[responseComponentName];

    if (!ResponseComponent) {
      return (
        <Alert variant="danger">
          <Alert.Heading>{intl.formatMessage(messages['ai.extensions.config.unknown.heading'])}</Alert.Heading>
          <p>{intl.formatMessage(messages['ai.extensions.config.unknown.response'], { componentName: responseComponentName })}</p>
          <p className="mb-0 text-muted small">
            {intl.formatMessage(messages['ai.extensions.config.available.components'], { components: Object.keys(COMPONENT_REGISTRY).join(', ') })}
          </p>
        </Alert>
      );
    }

    // Merge props with config
    const requestProps = mergeProps(additionalProps, requestComponentConfig);
    const responseProps = mergeProps({}, responseComponentConfig);

    return (
      <div className="configurable-ai-assistance w-100">
        {configError && (
          <Alert variant="warning" dismissible className="mb-2">
            <small>{intl.formatMessage(messages['ai.extensions.config.fallback.error'], { error: configError })}</small>
          </Alert>
        )}

        {/* Request Interface */}
        <RequestComponent
          isLoading={isLoading}
          hasAsked={hasAsked && !error}
          setResponse={setResponse}
          setHasAsked={setHasAsked}
          onAskAI={handleAskAI}
          disabled={false}
          {...requestProps}
        />

        {/* Response Interface - Now dynamic! */}
        <ResponseComponent
          response={response}
          error={error}
          isLoading={isLoading}
          onAskAgain={handleAskAI}
          onClear={handleReset}
          onError={handleClearError}
          contextData={additionalProps}
          {...responseProps}
        />
      </div>
    );
  }

  return null;
};

export default ConfigurableAIAssistance;
