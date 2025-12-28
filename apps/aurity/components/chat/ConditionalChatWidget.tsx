'use client';

/**
 * ConditionalChatWidget - Client Component Wrapper
 *
 * Wraps ChatWidget with route-aware conditional rendering.
 * This pattern keeps the root layout as a server component (preserving metadata)
 * while enabling client-side pathname detection.
 *
 * Best Practice Pattern:
 * - Root layout = Server Component (with metadata)
 * - This wrapper = Client Component (with usePathname)
 * - ChatWidget = Nested client component (interactive features)
 */

import { usePathname, useSearchParams } from 'next/navigation';
import { ChatWidget } from './ChatWidget';

/**
 * Routes where the floating ChatWidget should not appear
 */
const EXCLUDED_ROUTES = [
  '/chat', // Dedicated chat page (has its own fullscreen chat)
  '/receptionist', // Receptionist check-in page
  '/_not-found', // 404 page
];

/**
 * Routes where specific query params should hide the widget
 * Example: /dashboard?mode=tv → hide widget (TV mode has no mouse/keyboard)
 */
const EXCLUDED_QUERY_PARAMS = [
  { path: '/dashboard', param: 'mode', values: ['tv', 'recepcion'] },
];

export function ConditionalChatWidget() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Normalize pathname (remove trailing slash for consistent comparison)
  const normalizedPath = pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;

  // Don't render ChatWidget on excluded routes
  if (EXCLUDED_ROUTES.includes(normalizedPath)) {
    return null;
  }

  // Check query param exclusions (e.g., /dashboard?mode=tv)
  for (const exclusion of EXCLUDED_QUERY_PARAMS) {
    if (normalizedPath === exclusion.path) {
      const paramValue = searchParams.get(exclusion.param);
      if (paramValue && exclusion.values.includes(paramValue)) {
        return null;
      }
    }
  }

  return <ChatWidget />;
}
