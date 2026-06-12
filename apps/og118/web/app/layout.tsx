import type { Metadata, Viewport } from 'next';
import 'fi-glass/theme.css';
import './globals.css';
// B3-V2: adopt the reusable glassmorphism chat preset from fi-glass (B3-V1).
// Imported last so its opt-in `.glass-chat-*` classes win where og118 applies them.
import 'fi-glass/glass-chat.css';

export const metadata: Metadata = {
  title: 'og118.ai',
  description: 'soon. something radioactive here.',
  metadataBase: new URL('https://og118.ai'),
  alternates: { canonical: '/' },
  icons: { icon: '/favicon.png', apple: '/apple-touch-icon.png' },
  openGraph: {
    type: 'website',
    url: 'https://og118.ai/',
    title: 'og118.ai',
    description: 'soon. something radioactive here.',
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'og118.ai',
    description: 'soon. something radioactive here.',
    images: ['/og-image.png'],
  },
};

export const viewport: Viewport = {
  themeColor: '#0a0e16',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      {/* glass-chat: the reusable page-depth treatment (layered navy gradient,
          B3-FIGLASS-13); the watermark layer renders og118's brand via the
          --glass-chat-watermark-image token set in globals.css. */}
      <body className="glass-chat">
        <div className="glass-chat-watermark" aria-hidden />
        {children}
      </body>
    </html>
  );
}
