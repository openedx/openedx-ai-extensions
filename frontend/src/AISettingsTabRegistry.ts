/**
 * AI Settings Tab Registry
 *
 * A registry that allows plugins to register tabs into the AIExtensionsSettingsModal.
 * The modal assembles its tabs dynamically: the built-in Workflows tab comes first,
 * followed by all tabs registered here in registration order. All tabs are always shown.
 *
 * Usage (from an external plugin like openedx-ai-badges):
 *
 *   import { registerAISettingsTab } from '@openedx/openedx-ai-extensions-ui';
 *   import MyTab from './components/MyTab';
 *
 *   registerAISettingsTab({
 *     id: 'my-feature',
 *     label: 'My Feature',   // tab display label (plain string)
 *     component: MyTab,
 *   });
 */

import React from 'react';

export interface AISettingsTab {
  /**
   * Unique identifier for this tab.
   */
  id: string;

  /**
   * Display label shown on the tab. Plain string — plugins should pre-format
   * any i18n messages before registering.
   */
  label: string;

  /**
   * React component rendered as the tab body.
   */
  component: React.ComponentType<any>;
}

const AI_SETTINGS_TAB_REGISTRY: AISettingsTab[] = [];

/**
 * Register a tab in the AI Extensions Settings Modal.
 * Tabs are rendered in registration order after the built-in core tabs.
 *
 * @param tab - Tab configuration object
 */
export function registerAISettingsTab(tab: AISettingsTab): void {
  const alreadyRegistered = AI_SETTINGS_TAB_REGISTRY.some((t) => t.id === tab.id);
  if (alreadyRegistered) {
    // eslint-disable-next-line no-console
    console.warn(`[AISettingsTabRegistry] Tab with id "${tab.id}" is already registered. Skipping.`);
    return;
  }
  AI_SETTINGS_TAB_REGISTRY.push(tab);
}

/**
 * Returns a copy of all currently registered external tabs.
 */
export function getRegisteredAISettingsTabs(): AISettingsTab[] {
  return [...AI_SETTINGS_TAB_REGISTRY];
}
