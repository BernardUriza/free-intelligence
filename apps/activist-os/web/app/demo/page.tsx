import { Suspense } from 'react';
import DemoClient from './DemoClient';

export const metadata = {
  title: 'Activist OS — Coordination Demo',
  description:
    'The canonical coordination history of an Activist OS run — the CAMPAIGN ⇄ SAFETY veto loop, rendered from the real transport, not narrated.',
};

export default function DemoPage() {
  return (
    <Suspense fallback={null}>
      <DemoClient />
    </Suspense>
  );
}
