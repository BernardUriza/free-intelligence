import type { Metadata, Viewport } from 'next';
import 'fi-glass/theme.css';
import 'fi-glass/glass-chat.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fénix',
  description: 'El asistente de Servicios Papeleros Fénix — cotizaciones y documentos.',
  icons: {
    icon: [
      { url: '/branding/favicon.ico', sizes: 'any' },
      { url: '/branding/icon-192.png', type: 'image/png', sizes: '192x192' },
      { url: '/branding/icon-512.png', type: 'image/png', sizes: '512x512' },
    ],
    apple: '/branding/apple-touch-icon.png',
  },
  openGraph: {
    type: 'website',
    title: 'Fénix',
    description: 'El asistente de Servicios Papeleros Fénix — cotizaciones y documentos.',
    images: [{ url: '/branding/og-image.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Fénix',
    description: 'El asistente de Servicios Papeleros Fénix — cotizaciones y documentos.',
    images: ['/branding/twitter-card.png'],
  },
};

export const viewport: Viewport = {
  // El mismo --glass-chat-body que pinta el fondo de la app, para que la barra
  // del navegador en móvil no corte con un color distinto al de la página.
  themeColor: '#020617',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-MX">
      {/* HALLAZGO-5: la clase `glass-chat` NO es decorativa — es el interruptor
          del tema de fi-glass. Sin ella --fi-bg/--fi-surface/--fi-text quedan
          VACÍAS y el composer renderiza con fondo blanco sobre página negra.
          No está documentado: se descubre leyendo apps/og118/web/app/layout.tsx. */}
      <body className="glass-chat">{children}</body>
    </html>
  );
}
