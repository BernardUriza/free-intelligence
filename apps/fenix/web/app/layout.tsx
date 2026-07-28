import type { Metadata, Viewport } from 'next';
import 'fi-glass/theme.css';
import 'fi-glass/glass-chat.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fénix',
  description: 'El asistente de Servicios Papeleros Fénix',
};

export const viewport: Viewport = {
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
