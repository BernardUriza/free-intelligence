const STEPS = [
  'Click "Load Demo Dataset" to populate the application with sample data',
  'Explore sessions using the deep links above (Dashboard, Sessions, Timeline, Audit)',
  'Click on any session to view its interactions in the Viewer',
  'Use "Reset Demo" when done to clear all sample data',
] as const;

export function QuickStartGuide() {
  return (
    <section className="demo-guide">
      <h2 className="demo-guide-title">Quick Start Guide</h2>
      <ol className="demo-guide-steps">
        {STEPS.map((text, index) => (
          <li key={index} className="demo-guide-step">
            <span className="demo-step-number">{index + 1}</span>
            <span>{text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
