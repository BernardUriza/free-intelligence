import type { Metadata } from 'next';
import Script from 'next/script';
import 'fi-glass/theme.css';
import 'fi-glass/glass-chat.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Activist OS — Safe, evidence-backed civic advocacy workflows',
  description:
    'A multi-agent workflow for safe, evidence-backed civic advocacy. Band coordinates the agents. FI preserves memory and provenance. Safety gates every public action.',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="fi-shell-bg" />
        <canvas id="synapse" aria-hidden="true" />
        <Script src="/synapse-field.js" strategy="afterInteractive" />
        {children}
      </body>
    </html>
  );
}
