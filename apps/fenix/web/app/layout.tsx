import type { Metadata, Viewport } from 'next';
import './globals.css';

const NOMBRE = 'Servicios Papeleros Fénix';
const RESUMEN = 'Papelería en San Juan Bosco, Guadalajara. Cotizamos tu lista escolar por WhatsApp.';

export const metadata: Metadata = {
  // Sin esto Next resuelve las imágenes de Open Graph contra localhost y el enlace llega sin portada.
  metadataBase: new URL('https://www.serviciosfenix.com.mx'),
  title: NOMBRE,
  description: RESUMEN,
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
    title: NOMBRE,
    description: RESUMEN,
    images: [{ url: '/branding/og-image.png', width: 1200, height: 630 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: NOMBRE,
    description: RESUMEN,
    images: ['/branding/twitter-card.png'],
  },
};

export const viewport: Viewport = {
  themeColor: '#fdfaf4',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-MX">
      <body>{children}</body>
    </html>
  );
}
