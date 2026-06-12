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
