/**
 * Extension Registry
 *
 * Central registry for all plugin-contributed extensions. Two storage models
 * coexist here because they have genuinely different semantics:
 *
 *  - COMPONENTS registry  — a plain dict (O(1) lookup by id, silent overwrite).
 *    Used by ConfigurableAIAssistance to resolve component names from backend config.
 *
 *  - All other named registries — ordered arrays with duplicate-id guards.
 *    Used for things like settings tabs where insertion order and uniqueness matter.
 *
 * Known registry names live in REGISTRY_NAMES. Add a new entry there to introduce
 * a new registry; the storage and dispatch logic below pick it up automatically.
 *
 * Preferred registration API (from an external plugin):
 *
 *   import { registerComponents, REGISTRY_NAMES } from '@openedx/openedx-ai-extensions-ui';
 *
 *   // Workflow component
 *   registerComponents({ MyRequestComponent, MyResponseComponent });
 *
 *   // Settings tab
 *   registerComponents(REGISTRY_NAMES.SETTINGS, {
 *     id: 'my-feature',
 *     label: 'My Feature',
 *     component: MyTab,
 *   });
 */

import React from 'react';

// ---------------------------------------------------------------------------
// Registry names
// ---------------------------------------------------------------------------

/**
 * Known registry names. Adding a new entry here is all that's needed to
 * introduce a new named registry.
 */
export const REGISTRY_NAMES = {
  /** Workflow UI components looked up by name from backend config. */
  COMPONENTS: 'components',
  /** Tabs rendered inside AIExtensionsSettingsModal. */
  SETTINGS: 'settings',
} as const;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * A generic registry entry. `label` is optional — it's only required for
 * registries that render it in a UI (e.g. SETTINGS tabs).
 */
export interface RegistryEntry {
  id: string;
  label?: string;
  component: React.ComponentType<any>;
}

/**
 * A settings tab entry — a RegistryEntry where `label` is required.
 * Kept for backward compatibility with existing plugin code.
 */
export interface AISettingsTab extends RegistryEntry {
  label: string;
}

// ---------------------------------------------------------------------------
// Storage
// ---------------------------------------------------------------------------

/**
 * Fast dict for COMPONENTS registry. Silent overwrite matches the original
 * COMPONENT_REGISTRY behaviour and avoids HMR warnings on re-registration.
 */
const COMPONENT_STORE: Record<string, React.ComponentType<any>> = {};

/**
 * Ordered arrays for all other named registries.
 * Entries are kept in insertion order; duplicate ids are rejected with a warning.
 */
const NAMED_REGISTRIES: Record<string, RegistryEntry[]> = {};

// ---------------------------------------------------------------------------
// Generic API
// ---------------------------------------------------------------------------

/**
 * Register an entry into a named registry.
 *
 * - COMPONENTS registry: dict-style, silently overwrites existing entries.
 * - All other registries: array-style, skips duplicate ids with a console warning.
 *
 * @param registryName - A value from REGISTRY_NAMES (or any string for future registries)
 * @param entry - The entry to register
 */
export function registerEntry(registryName: string, entry: RegistryEntry): void {
  if (registryName === REGISTRY_NAMES.COMPONENTS) {
    COMPONENT_STORE[entry.id] = entry.component;
    return;
  }

  if (!NAMED_REGISTRIES[registryName]) {
    NAMED_REGISTRIES[registryName] = [];
  }
  const alreadyRegistered = NAMED_REGISTRIES[registryName].some((e) => e.id === entry.id);
  if (alreadyRegistered) {
    // eslint-disable-next-line no-console
    console.warn(`[Registry "${registryName}"] Entry with id "${entry.id}" is already registered. Skipping.`);
    return;
  }
  NAMED_REGISTRIES[registryName].push(entry);
}

/**
 * Returns a copy of all entries currently registered under a given registry name.
 *
 * @param registryName - A value from REGISTRY_NAMES
 */
export function getEntries(registryName: string): RegistryEntry[] {
  if (registryName === REGISTRY_NAMES.COMPONENTS) {
    return Object.entries(COMPONENT_STORE).map(([id, component]) => ({ id, component }));
  }
  return [...(NAMED_REGISTRIES[registryName] ?? [])];
}

/**
 * Look up a single workflow component by name. O(1).
 * Returns undefined if the component has not been registered.
 *
 * @param name - The component name as specified in backend config
 */
export function getComponent(name: string): React.ComponentType<any> | undefined {
  return COMPONENT_STORE[name];
}
