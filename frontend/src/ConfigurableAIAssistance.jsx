import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { Spinner, Alert } from '@openedx/paragon';

// Import services
import {
  fetchConfiguration,
  getDefaultEndpoint,
  mergeProps,
  prepareContextData,
} from './services';

// Import available components
import GetAIAssistanceButton from './GetAIAssistanceButton';

/**
 * Component Registry
 * Maps component names from config to actual React components
 */
const COMPONENT_REGISTRY = {
  GetAIAssistanceButton,
  // Future components can be added here
  // 'CustomAIComponent': CustomAIComponent,
};

/**
 * Configurable AI Assistance Wrapper Component
 *
 * Fetches runtime configuration from an API and dynamically renders
 * the appropriate AI assistance component with the specified configuration.
 *
 * Advanced users can skip this wrapper and use GetAIAssistanceButton directly.
 */
const ConfigurableAIAssistance = ({
  configEndpoint,
  courseId,
  unitId,
  sequence,
  fallbackConfig,
  onConfigLoad,
  onConfigError,
  ...additionalProps
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [config, setConfig] = useState(null);

  const endpoint = configEndpoint || getDefaultEndpoint('config');
  const requestIdRef = useRef(0);

  useEffect(() => {
    const abortController = new AbortController();
    const currentRequestId = ++requestIdRef.current;

    const loadConfiguration = async () => {
      setIsLoading(true);
      setError(null);

      const contextData = prepareContextData({
        sequence,
        courseId,
        unitId,
        ...additionalProps,
      });

      try {
        const fetchedConfig = await fetchConfiguration({
          configEndpoint: endpoint,
          contextData,
          signal: abortController.signal,
        });

        // Only update state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          setConfig(fetchedConfig);

          if (onConfigLoad) {
            onConfigLoad(fetchedConfig);
          }

          // eslint-disable-next-line no-console
          console.log('[ConfigurableAIAssistance] Configuration loaded:', fetchedConfig);
        }
      } catch (err) {
        // Ignore aborted requests
        if (err.name === 'AbortError' || err.message?.includes('aborted')) {
          // eslint-disable-next-line no-console
          console.log('[ConfigurableAIAssistance] Request aborted');
          return;
        }

        // Only update state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          // eslint-disable-next-line no-console
          console.error('[ConfigurableAIAssistance] Configuration error:', err);

          setError(err.message);

          if (fallbackConfig) {
            setConfig(fallbackConfig);
            // eslint-disable-next-line no-console
            console.log('[ConfigurableAIAssistance] Using fallback configuration');
          }

          if (onConfigError) {
            onConfigError(err);
          }
        }
      } finally {
        // Only update loading state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          setIsLoading(false);
        }
      }
    };

    loadConfiguration();

    return () => {
      abortController.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  if (isLoading) {
    return (
      <div className="d-flex align-items-center gap-2 p-3">
        <Spinner animation="border" size="sm" />
      </div>
    );
  }

  if (error && !config) {
    return (
      <Alert variant="danger">
        <Alert.Heading>Configuration Error</Alert.Heading>
        <p>Failed to load AI extensions configuration: {error}</p>
      </Alert>
    );
  }

  if (config) {
    const { component: componentName, config: componentConfig = {} } = config;
    const ComponentToRender = COMPONENT_REGISTRY[componentName];

    if (!ComponentToRender) {
      return (
        <Alert variant="warning">
          <Alert.Heading>Unknown Component</Alert.Heading>
          <p>Component &quot;{componentName}&quot; is not available.</p>
          <p className="mb-0 text-muted small">
            Available components: {Object.keys(COMPONENT_REGISTRY).join(', ')}
          </p>
        </Alert>
      );
    }

    const mergedProps = mergeProps(additionalProps, componentConfig);
    const finalProps = {
      ...mergedProps,
      sequence,
      courseId,
      unitId,
    };

    // eslint-disable-next-line no-console
    console.log('[ConfigurableAIAssistance] Rendering component:', componentName, 'with props:', finalProps);

    return (
      <div className="configurable-ai-assistance">
        {error && (
          <Alert variant="warning" dismissible className="mb-2">
            <small>Using fallback configuration due to error: {error}</small>
          </Alert>
        )}

        <ComponentToRender {...finalProps} />
      </div>
    );
  }

  return null;
};

ConfigurableAIAssistance.propTypes = {
  configEndpoint: PropTypes.string,
  courseId: PropTypes.string,
  unitId: PropTypes.string,
  sequence: PropTypes.shape({
    id: PropTypes.string,
    displayName: PropTypes.string,
    unitBlocks: PropTypes.arrayOf(PropTypes.shape({})),
  }),
  fallbackConfig: PropTypes.shape({
    component: PropTypes.string.isRequired,
    config: PropTypes.shape({}),
  }),
  onConfigLoad: PropTypes.func,
  onConfigError: PropTypes.func,
};

ConfigurableAIAssistance.defaultProps = {
  configEndpoint: null,
  courseId: null,
  unitId: null,
  sequence: null,
  fallbackConfig: null,
  onConfigLoad: null,
  onConfigError: null,
};

export default ConfigurableAIAssistance;
