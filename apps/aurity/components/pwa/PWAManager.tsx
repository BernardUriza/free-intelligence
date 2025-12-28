'use client';

// =============================================================================
// PWA Manager - Orchestrates all PWA UI components
// =============================================================================
// Single Responsibility: Composes and renders PWA UI elements
// Open/Closed: Add new PWA features without modifying this component
// =============================================================================

import { InstallPrompt } from './InstallPrompt';
import { OfflineIndicator } from './OfflineIndicator';
import { UpdatePrompt } from './UpdatePrompt';

/**
 * PWAManager renders all PWA-related UI components.
 * Must be used inside a PWAProvider.
 *
 * Components rendered:
 * - OfflineIndicator: Shows when device is offline
 * - UpdatePrompt: Shows when a new version is available
 * - InstallPrompt: Shows install prompt for supported platforms
 */
export function PWAManager() {
  return (
    <>
      <OfflineIndicator />
      <UpdatePrompt />
      <InstallPrompt />
    </>
  );
}
