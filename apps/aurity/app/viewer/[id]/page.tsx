/**
 * Interaction Viewer Page
 * Card: FI-UI-FEAT-205
 *
 * Server component wrapper for static export compatibility
 * Route: /viewer/:id?index=N
 */

// Required for static export with dynamic routes
// Returns a placeholder to work around Next.js bug with empty arrays
// See: https://github.com/vercel/next.js/issues/71862
export function generateStaticParams() {
  return [{ id: 'placeholder' }];
}

// Client component import
import ViewerClient from './ViewerClient';

export default function ViewerPage() {
  return <ViewerClient />;
}
