import type { Metadata } from 'next';
import Script from 'next/script';
import 'fi-glass/theme.css';
import 'fi-glass/glass-chat.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Activist OS',
  description: 'A multi-agent workflow for safe, evidence-backed civic advocacy.',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        {/* The living backdrop: radial field + synapse flow field (six attractors,
            one per agent). Mounted once in the layout so every route gets it. */}
        <div className="fi-shell-bg" />
        <canvas id="synapse" aria-hidden="true" />
        <Script src="/synapse-field.js" strategy="afterInteractive" />
        {children}
      </body>
    </html>
  );
}
