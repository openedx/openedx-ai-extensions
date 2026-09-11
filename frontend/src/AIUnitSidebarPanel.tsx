import React, { createContext, useContext, useMemo } from 'react';
import { getConfig } from '@edx/frontend-platform';
import type { IntlShape } from '@edx/frontend-platform/i18n';
import { Stack } from '@openedx/paragon';
import { AutoAwesome } from '@openedx/paragon/icons';

import ConfigurableAIAssistance from './ConfigurableAIAssistance';
import messages from './messages';

/**
 * `react-intl`'s own `MessageDescriptor`, reached through frontend-platform so
 * that this package pins one intl version rather than two.
 */
type MessageDescriptor = Parameters<IntlShape['formatMessage']>[0];

/**
 * Studio's `isUnitPageNewDesignEnabled`, inlined rather than imported: this
 * package must stay free of authoring internals. With the flag off Studio
 * renders the legacy sidebar, which ignores the pages context entirely, so a
 * page registered there would never be shown.
 */
const isPagedSidebarActive = () => (
  (getConfig().ENABLE_UNIT_PAGE_NEW_DESIGN?.toString().toLowerCase() ?? 'true') === 'true'
);

/**
 * A single AI box rendered inside the sidebar page.
 *
 * `selectorId` is the `ui_slot_selector_id` the backend resolves a workflow
 * profile against. A box whose selector has no configured scope resolves to a
 * 404 and hides itself, so listing a box is always safe.
 */
export interface AISidebarBox {
  selectorId: string;
}

/**
 * Kept as the default so existing AIWorkflowScope rows, which were written
 * against the widget id of the old `Insert` contribution, keep matching.
 */
export const DEFAULT_UNIT_SIDEBAR_BOXES: AISidebarBox[] = [
  { selectorId: 'ai-assist-button-course-outline-sidebar' },
];

interface BoxProps {
  boxes: AISidebarBox[];
  context: Record<string, any>;
}

/**
 * Carries the unit context down to the page, which Studio's sidebar renders
 * with no props of its own.
 */
const BoxPropsContext = createContext<BoxProps>({
  boxes: DEFAULT_UNIT_SIDEBAR_BOXES,
  context: {},
});

/**
 * Stand-in used when the host gives us no pages context, so that `useContext`
 * is still called unconditionally.
 */
const NoPagesContext = createContext<any>(undefined);

/**
 * The AI page itself: one box per configured selector.
 *
 * Defined at module scope so its identity is constant. Studio stores it in the
 * sidebar's pages object, and a fresh component type on every render would
 * remount the whole page and lose its state.
 */
const AIExtensionsSidebarPage = () => {
  const { boxes, context } = useContext(BoxPropsContext);

  return (
    <Stack gap={3} className="pt-3">
      {boxes.map((box) => (
        <ConfigurableAIAssistance
          key={box.selectorId}
          uiSlotSelectorId={box.selectorId}
          {...context}
        />
      ))}
    </Stack>
  );
};

interface AIUnitSidebarPanelProps {
  /** The wrapped default sidebar, handed over by the FPF `Wrap` operation. */
  children?: React.ReactNode;
  /**
   * Studio's `UnitSidebarPagesContext`, passed in by `env.config.jsx` rather
   * than imported here: this package must stay free of authoring internals so
   * it can be built once and shipped to every Open edX release.
   */
  PagesContext?: React.Context<any> | null;
  boxes?: AISidebarBox[];
  icon?: React.ComponentType;
  pageKey?: string;
  /** Formatted by Studio's Sidebar for the page heading and icon label. */
  title?: MessageDescriptor;
  courseId?: string | null;
  blockId?: string | null;
  unitTitle?: string | null;
  readOnly?: boolean;
  /** The slot passes more props than the boxes need; the rest are ignored. */
  [key: string]: any;
}

/**
 * Adds the AI extensions page to Studio's paged unit sidebar.
 *
 * Wraps the unit sidebar and re-provides its pages context with one extra
 * page, so the sparkle icon joins the sidebar's icon rail and the AI boxes
 * open, collapse and resize along with every other page.
 *
 * When the paged sidebar is not the one rendering — an older release that has
 * no pages context, or Verawood with ENABLE_UNIT_PAGE_NEW_DESIGN turned off —
 * this wrapper is inert and hands the sidebar straight back. The legacy
 * sidebar gets its boxes from the `course_unit_sidebar.v1` contribution
 * instead, which renders inside the sidebar's own padded, width-capped column
 * rather than as an unstyled block hanging below it.
 */
const AIUnitSidebarPanel = ({
  children = null,
  PagesContext = null,
  boxes = DEFAULT_UNIT_SIDEBAR_BOXES,
  icon = AutoAwesome,
  pageKey = 'aiExtensions',
  title = messages['ai.extensions.unit.sidebar.title'],
  courseId = null,
  blockId = null,
  unitTitle = null,
  readOnly = false,
}: AIUnitSidebarPanelProps) => {
  // Forwarded explicitly rather than by spreading the slot's props: a fresh
  // object every render would make this memo pointless, and the page would
  // re-render on every keystroke elsewhere in the unit.
  const boxProps = useMemo<BoxProps>(
    () => ({
      boxes,
      context: {
        courseId, locationId: blockId, unitTitle, readOnly,
      },
    }),
    [boxes, courseId, blockId, unitTitle, readOnly],
  );

  const ActiveContext = PagesContext ?? NoPagesContext;
  const existingPages = useContext(ActiveContext);

  // Both conditions matter: Studio mounts `UnitSidebarPagesProvider` whatever
  // the flag says, so a defined context is no proof that the paged sidebar is
  // the one on screen.
  const pages = useMemo(
    () => (existingPages && isPagedSidebarActive()
      ? {
        ...existingPages,
        [pageKey]: { component: AIExtensionsSidebarPage, icon, title },
      }
      : null),
    [existingPages, pageKey, icon, title],
  );

  // Without pages the sidebar is handed straight back: rendering the boxes
  // here as well would double them up wherever the v1 contribution also
  // applies. The outer provider is then inert, and kept only for one shape.
  return (
    <BoxPropsContext.Provider value={boxProps}>
      {pages ? (
        <ActiveContext.Provider value={pages}>{children}</ActiveContext.Provider>
      ) : (
        children
      )}
    </BoxPropsContext.Provider>
  );
};

export default AIUnitSidebarPanel;
