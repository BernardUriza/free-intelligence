import type { Metadata } from 'next';
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
      <body>{children}</body>
    </html>
  );
}
