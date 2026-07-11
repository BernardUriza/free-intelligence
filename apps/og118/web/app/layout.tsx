import type { Metadata, Viewport } from 'next';
import 'fi-glass/theme.css';
import './globals.css';
// B3-V2: adopt the reusable glassmorphism chat preset from fi-glass (B3-V1).
// Imported last so its opt-in `.glass-chat-*` classes win where og118 applies them.
import 'fi-glass/glass-chat.css';

// INSTALLABLE ON iOS WITHOUT A WEB APP MANIFEST — ON PURPOSE.
//
// iOS reads the manifest's `scope` to decide which URLs may stay in standalone
// mode. Auth0 lives on another origin, so the login redirect is ALWAYS
// out-of-scope: with a manifest present, iOS drops standalone, finishes the
// login in a browser whose storage it does not share with the installed app,
// and the PWA comes back still signed out.
//
// `apple-mobile-web-app-capable` (Next: `appleWebApp.capable`) grants standalone
// WITHOUT introducing a scope, so the Auth0 round-trip survives. Adding a
// manifest.json here would break sign-in on iPhone. Don't.
export const metadata: Metadata = {
  title: 'og118',
  description: 'Tu agente og118 — conversaciones, proyectos y voz.',
  metadataBase: new URL('https://og118.ai'),
  alternates: { canonical: '/' },
  icons: { icon: '/favicon.png', apple: '/apple-touch-icon.png' },
  // `black-translucent` renders the web view FULL-BLEED under the status bar —
  // the native look (ChatGPT does this). Safe now that the shell pads its top by
  // env(safe-area-inset-top) (B3-FIGLASS-MOBILE-NATIVE-1), so the clock overlays
  // the background, not the content. og118's page is dark, so the white
  // status-bar glyphs stay legible.
  appleWebApp: {
    capable: true,
    title: 'og118',
    statusBarStyle: 'black-translucent',
  },
  // `appleWebApp.capable` does NOT emit `apple-mobile-web-app-capable` on
  // Next >= 15: PR vercel/next.js#70363 swapped it for the unprefixed
  // `mobile-web-app-capable` because Chrome flagged the Apple tag as
  // deprecated. Safari reads ONLY the prefixed one (Apple, "Configuring Web
  // Applications"), so without this line "Add to Home Screen" opens a plain
  // Safari tab instead of a standalone app. Verified against the emitted
  // out/index.html, not against the config. See next.js#70272, #74524.
  other: { 'apple-mobile-web-app-capable': 'yes' },
  openGraph: {
    type: 'website',
    url: 'https://og118.ai/',
    title: 'og118',
    description: 'Tu agente og118 — conversaciones, proyectos y voz.',
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'og118',
    description: 'Tu agente og118 — conversaciones, proyectos y voz.',
    images: ['/og-image.png'],
  },
};

export const viewport: Viewport = {
  themeColor: '#0a0e16',
  width: 'device-width',
  initialScale: 1,
  // Full-bleed to the physical screen edges. Without it iOS letterboxes the
  // view and every env(safe-area-inset-*) resolves to 0 — which is exactly the
  // value fi-glass's composer relies on to clear the home indicator.
  viewportFit: 'cover',
  // Pinch-zoom stays ENABLED (WCAG 1.4.4). The usual reason to disable it —
  // iOS auto-zooming on input focus — does not apply: that only fires under a
  // 16px font, and the composer textarea already computes to exactly 16px.
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
