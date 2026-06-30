// fi-glass test setup.
//
// jsdom does not implement ResizeObserver, but use-stick-to-bottom (the
// pin-to-bottom engine wired into AgentConversationSurface, B3-FIGLASS-12)
// constructs one as soon as its scroll ref attaches. A no-op stub keeps jsdom
// component tests rendering; scroll-pinning behavior itself is verified in the
// browser (staging smoke), not in jsdom.
if (typeof globalThis.ResizeObserver === 'undefined') {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}

// jsdom does not implement matchMedia, but useMediaQuery (the responsive engine
// behind AgentWorkspaceShell's mobile drawer and AgentConversationSurface's
// mobile inset, B3-FIGLASS-MOBILE-1) calls it on render. A non-matching stub
// keeps jsdom component tests rendering at the desktop breakpoint; a test that
// needs a specific breakpoint overrides window.matchMedia itself (and clears the
// useMediaQuery cache between cases).
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
