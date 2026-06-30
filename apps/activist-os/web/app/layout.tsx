import type { Metadata } from 'next';
import Script from 'next/script';
import 'fi-glass/theme.css';
import 'fi-glass/glass-chat.css';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://aos.bernarduriza.com'),
  title: 'Activist OS — Safe, evidence-backed civic advocacy workflows',
  description:
    'A multi-agent workflow for safe, evidence-backed civic advocacy. Band coordinates the agents. FI preserves memory and provenance. Safety gates every public action.',
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/branding/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/branding/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: '/branding/apple-touch-icon.png',
  },
  openGraph: {
    type: 'website',
    url: 'https://aos.bernarduriza.com/',
    title: 'Activist OS — Safe, evidence-backed civic advocacy workflows',
    description:
      'Coordinate specialized agents to turn a community concern into a verified campaign packet — with provenance, safety review, and human-action tasks before anything goes public.',
    images: [{ url: '/branding/og-image.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Activist OS — Safe, evidence-backed civic advocacy',
    description: 'Band coordinates the agents. FI preserves memory and provenance. Safety gates every public action.',
    images: ['/branding/twitter-card.png'],
  },
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
