import { createContext, useContext } from 'react';
import { mergeConfig } from '@edx/frontend-platform';
import { screen, waitFor } from '@testing-library/react';
import { fetchConfiguration } from './services';
import { renderWrapper as render } from './setupTest';
import AIUnitSidebarPanel, { DEFAULT_UNIT_SIDEBAR_BOXES } from './AIUnitSidebarPanel';

jest.mock('./ConfigurableAIAssistance', () => ({
  __esModule: true,
  default: (props: any) => (
    <div
      data-testid="ai-box"
      data-selector={props.uiSlotSelectorId}
      data-course={props.courseId ?? ''}
      data-location={props.locationId ?? ''}
      data-unit-title={props.unitTitle ?? ''}
    />
  ),
}));

jest.mock('./services', () => ({
  fetchConfiguration: jest.fn(),
  getDefaultEndpoint: () => 'http://localhost:18010/openedx-ai-extensions/v1/profile/',
  prepareContextData: (context: any) => context,
}));

const mockFetchConfiguration = fetchConfiguration as jest.Mock;

/** What the panel's profile probe resolves to, by selector id. */
const probeResolves = (configured: Record<string, boolean>) => {
  mockFetchConfiguration.mockImplementation(
    ({ contextData }: any) => Promise.resolve(configured[contextData.uiSlotSelectorId] ? {} : null),
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  // Left in flight by default: tests that are not about the probe would
  // otherwise settle it after their assertions have run, outside `act`.
  mockFetchConfiguration.mockReturnValue(new Promise(() => {}));
});

const contextProps = {
  courseId: 'course-v1:edunext+01+2026-mit',
  blockId: 'block-v1:edunext+01+2026-mit+type@vertical+block@abc',
};

const boxSelectors = () => screen.getAllByTestId('ai-box').map((el) => el.getAttribute('data-selector'));

/**
 * Studio reads `ENABLE_UNIT_PAGE_NEW_DESIGN` as a string and treats anything
 * but 'false' as on, so 'true' is the right value to reset to. `mergeConfig`
 * warns on an undefined value, which rules out deleting the key instead.
 */
const setNewUnitDesign = (value: string) => {
  mergeConfig({ ENABLE_UNIT_PAGE_NEW_DESIGN: value });
};

afterEach(() => setNewUnitDesign('true'));

/**
 * The wrapper is inert wherever the paged sidebar is not the one rendering:
 * there the boxes come from the `course_unit_sidebar.v1` contribution, which
 * renders inside the legacy sidebar's own column. Rendering them here as well
 * would show two of every box.
 */
describe('AIUnitSidebarPanel outside the paged sidebar', () => {
  const defaultSidebar = <div data-testid="default-sidebar">default sidebar</div>;

  const expectUntouchedSidebar = () => {
    expect(screen.getByTestId('default-sidebar')).toBeInTheDocument();
    expect(screen.queryByTestId('ai-box')).not.toBeInTheDocument();
  };

  it('hands back a sidebar it was given no pages context for', () => {
    render(
      <AIUnitSidebarPanel {...contextProps}>
        {defaultSidebar}
      </AIUnitSidebarPanel>,
    );

    expectUntouchedSidebar();
  });

  it('hands back a sidebar whose pages context has no provider', () => {
    const PagesContext = createContext<any>(undefined);

    render(
      <AIUnitSidebarPanel PagesContext={PagesContext} {...contextProps}>
        {defaultSidebar}
      </AIUnitSidebarPanel>,
    );

    expectUntouchedSidebar();
  });
});

describe('AIUnitSidebarPanel with a pages context', () => {
  const existingPage = {
    component: () => null,
    icon: () => null,
    title: { id: 'existing', defaultMessage: 'Info' },
  };

  /**
   * Renders the panel behind a stand-in for Studio's Sidebar, which reads the
   * pages context and renders the selected page.
   */
  const renderWithPages = ({ pageKey = 'aiExtensions', openPage = false, ...props }: any = {}) => {
    const PagesContext = createContext<any>(undefined);
    let captured: any;

    const FakeSidebar = () => {
      captured = useContext(PagesContext);
      const Page = captured?.[pageKey]?.component;
      return (
        <div data-testid="default-sidebar">
          {openPage && Page ? <Page /> : null}
        </div>
      );
    };

    const panel = (extraProps: any = {}) => (
      <PagesContext.Provider value={{ info: existingPage }}>
        <AIUnitSidebarPanel
          PagesContext={PagesContext}
          pageKey={pageKey}
          {...contextProps}
          {...props}
          {...extraProps}
        >
          <FakeSidebar />
        </AIUnitSidebarPanel>
      </PagesContext.Provider>
    );

    const { rerender } = render(panel());

    return {
      getPages: () => captured,
      rerenderWith: (extraProps: any) => rerender(panel(extraProps)),
    };
  };

  it('adds one page without dropping the existing ones', () => {
    const { getPages } = renderWithPages();

    expect(Object.keys(getPages())).toEqual(['info', 'aiExtensions']);
    expect(getPages().info).toBe(existingPage);
  });

  it('gives the page an icon and a title, and appends nothing to the sidebar', () => {
    const { getPages } = renderWithPages();
    const page = getPages().aiExtensions;

    expect(page.icon).toBeDefined();
    expect(page.title).toEqual(expect.objectContaining({ id: 'ai.extensions.unit.sidebar.title' }));
    expect(screen.getByTestId('default-sidebar')).toBeInTheDocument();
    expect(screen.queryByTestId('ai-box')).not.toBeInTheDocument();
  });

  it('honours a custom page key and icon', () => {
    const icon = () => null;
    const { getPages } = renderWithPages({ pageKey: 'quizzes', icon });

    expect(getPages().quizzes.icon).toBe(icon);
    expect(getPages().aiExtensions).toBeUndefined();
  });

  it('renders the default box when no list is configured', () => {
    renderWithPages({ openPage: true });

    expect(boxSelectors()).toEqual(DEFAULT_UNIT_SIDEBAR_BOXES.map((box) => box.selectorId));
  });

  it('renders one box per configured selector, with the unit context', () => {
    renderWithPages({
      openPage: true,
      boxes: [{ selectorId: 'quiz-generator' }, { selectorId: 'flashcards' }],
      unitTitle: 'Course Outline',
    });

    expect(boxSelectors()).toEqual(['quiz-generator', 'flashcards']);
    const [first] = screen.getAllByTestId('ai-box');
    expect(first).toHaveAttribute('data-course', contextProps.courseId);
    expect(first).toHaveAttribute('data-location', contextProps.blockId);
    expect(first).toHaveAttribute('data-unit-title', 'Course Outline');
  });

  it('keeps the page component identity stable across re-renders', () => {
    const { getPages, rerenderWith } = renderWithPages();
    const before = getPages().aiExtensions.component;

    rerenderWith({ unitTitle: 'Changed' });

    expect(getPages().aiExtensions.component).toBe(before);
  });

  it('reads the current unit context after a re-render', () => {
    const { rerenderWith } = renderWithPages({ openPage: true });

    rerenderWith({ courseId: 'course-v1:edunext+02+2026', blockId: 'block-v1:other' });

    const [box] = screen.getAllByTestId('ai-box');
    expect(box).toHaveAttribute('data-course', 'course-v1:edunext+02+2026');
    expect(box).toHaveAttribute('data-location', 'block-v1:other');
  });

  /**
   * The icon has to be drawn before any box has mounted, so the panel probes
   * the profiles itself and greys the icon out when there is nothing to open.
   * Studio renders a page carrying a `tooltip` as an `IconButtonWithTooltip`.
   */
  describe('profile probe', () => {
    const twoBoxes = [{ selectorId: 'quiz-generator' }, { selectorId: 'flashcards' }];
    const aiPage = (getPages: () => any) => getPages().aiExtensions;

    it('disables the page and explains why when no selector is configured', async () => {
      probeResolves({});

      const { getPages } = renderWithPages({ boxes: twoBoxes });

      await waitFor(() => expect(aiPage(getPages).disabled).toBe(true));
      expect(aiPage(getPages).tooltip).toEqual(
        expect.objectContaining({ id: 'ai.extensions.unit.sidebar.disabled.tooltip' }),
      );
    });

    it('enables the page with no tooltip when one selector is configured', async () => {
      probeResolves({ flashcards: true });

      const { getPages } = renderWithPages({ boxes: twoBoxes });

      await waitFor(() => expect(aiPage(getPages).disabled).toBe(false));
      expect(aiPage(getPages).tooltip).toBeUndefined();
    });

    it('keeps the page disabled and untooltipped while the probe is in flight', () => {
      mockFetchConfiguration.mockReturnValue(new Promise(() => {}));

      const { getPages } = renderWithPages({ boxes: twoBoxes });

      expect(aiPage(getPages).disabled).toBe(true);
      expect(aiPage(getPages).tooltip).toBeUndefined();
    });

    it('leaves the page open when a probe fails, rather than hiding the tool', async () => {
      mockFetchConfiguration.mockRejectedValue(new Error('gateway timeout'));

      const { getPages } = renderWithPages({ boxes: twoBoxes });

      await waitFor(() => expect(aiPage(getPages).disabled).toBe(false));
      expect(aiPage(getPages).tooltip).toBeUndefined();
    });

    it('probes once per selector, with the unit context', async () => {
      probeResolves({ flashcards: true });

      renderWithPages({ boxes: twoBoxes });

      await waitFor(() => expect(mockFetchConfiguration).toHaveBeenCalledTimes(2));
      expect(mockFetchConfiguration.mock.calls.map(([args]) => args.contextData)).toEqual([
        expect.objectContaining({ uiSlotSelectorId: 'quiz-generator', courseId: contextProps.courseId }),
        expect.objectContaining({ uiSlotSelectorId: 'flashcards', locationId: contextProps.blockId }),
      ]);
    });
  });

  /**
   * Studio mounts `UnitSidebarPagesProvider` whatever the flag says, then
   * renders the legacy sidebar, which never reads the pages context. A page
   * registered there would simply be invisible.
   */
  describe('but the new unit design turned off', () => {
    it.each(['false', 'False'])('registers no page when the flag is %s', (value) => {
      setNewUnitDesign(value);

      const { getPages } = renderWithPages({ openPage: true });

      expect(getPages().aiExtensions).toBeUndefined();
      expect(screen.getByTestId('default-sidebar')).toBeInTheDocument();
      expect(screen.queryByTestId('ai-box')).not.toBeInTheDocument();
    });

    it('registers the page again once the flag is back on', () => {
      setNewUnitDesign('true');

      const { getPages } = renderWithPages();

      expect(getPages().aiExtensions).toBeDefined();
    });
  });
});
