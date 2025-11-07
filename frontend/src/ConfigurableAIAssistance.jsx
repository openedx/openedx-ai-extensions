import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Spinner, Alert } from '@openedx/paragon';

// Import services
import {
  fetchConfiguration,
  mergeProps,
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
  useMock,
  courseId,
  unitId,
  fallbackConfig,
  onConfigLoad,
  onConfigError,
  ...additionalProps
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [config, setConfig] = useState(null);

  useEffect(() => {
    const loadConfiguration = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const fetchedConfig = await fetchConfiguration({
          configEndpoint,
          courseId,
          unitId,
          useMock,
        });

        setConfig(fetchedConfig);

        if (onConfigLoad) {
          onConfigLoad(fetchedConfig);
        }

        // eslint-disable-next-line no-console
        console.log('[ConfigurableAIAssistance] Configuration loaded:', fetchedConfig);
      } catch (err) {
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
      } finally {
        setIsLoading(false);
      }
    };

    loadConfiguration();
  }, [configEndpoint, courseId, unitId, useMock, fallbackConfig, onConfigLoad, onConfigError]);

  if (isLoading) {
    return (
      <div className="d-flex align-items-center gap-2 p-3">
        <Spinner animation="border" size="sm" />
        <span className="text-muted">Loading AI assistant configuration...</span>
      </div>
    );
  }

  if (error && !config) {
    return (
      <Alert variant="danger">
        <Alert.Heading>Configuration Error</Alert.Heading>
        <p>Failed to load AI assistance configuration: {error}</p>
        <p className="mb-0 text-muted small">
          Advanced users can use GetAIAssistanceButton component directly.
        </p>
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
  useMock: PropTypes.bool,
  courseId: PropTypes.string,
  unitId: PropTypes.string,
  fallbackConfig: PropTypes.shape({
    component: PropTypes.string.isRequired,
    config: PropTypes.shape({}),
  }),
  onConfigLoad: PropTypes.func,
  onConfigError: PropTypes.func,
};

ConfigurableAIAssistance.defaultProps = {
  configEndpoint: null,
  useMock: true,
  courseId: null,
  unitId: null,
  fallbackConfig: null,
  onConfigLoad: null,
  onConfigError: null,
};

export default ConfigurableAIAssistance;
