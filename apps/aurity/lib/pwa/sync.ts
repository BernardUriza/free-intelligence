// =============================================================================
// PWA Background Sync Manager
// =============================================================================
// Handles syncing queued actions when device comes back online
// =============================================================================

import { getQueuedActions, removeQueuedAction, QueuedAction } from './storage';

type SyncHandler = (action: QueuedAction) => Promise<boolean>;

const syncHandlers = new Map<string, SyncHandler>();

/**
 * Register a handler for a specific action type
 */
export function registerSyncHandler(type: string, handler: SyncHandler): void {
  syncHandlers.set(type, handler);
  console.log('[Sync] Registered handler for:', type);
}

/**
 * Process all queued actions
 */
export async function processQueue(): Promise<{ success: number; failed: number }> {
  const actions = await getQueuedActions();
  let success = 0;
  let failed = 0;

  console.log('[Sync] Processing queue:', actions.length, 'actions');

  for (const action of actions) {
    const handler = syncHandlers.get(action.type);

    if (!handler) {
      console.warn('[Sync] No handler for action type:', action.type);
      failed++;
      continue;
    }

    try {
      const result = await handler(action);

      if (result && action.id) {
        await removeQueuedAction(action.id);
        success++;
        console.log('[Sync] Action synced:', action.type);
      } else {
        failed++;
      }
    } catch (error) {
      console.error('[Sync] Failed to sync action:', action.type, error);
      failed++;
    }
  }

  console.log('[Sync] Queue processed. Success:', success, 'Failed:', failed);
  return { success, failed };
}

/**
 * Initialize sync manager - listens for online events
 */
export function initSyncManager(): () => void {
  const handleOnline = async () => {
    console.log('[Sync] Device online, processing queue...');
    await processQueue();
  };

  window.addEventListener('online', handleOnline);

  // Process queue on init if online
  if (navigator.onLine) {
    processQueue();
  }

  // Return cleanup function
  return () => {
    window.removeEventListener('online', handleOnline);
  };
}

/**
 * Request background sync (if supported)
 */
export async function requestBackgroundSync(tag: string = 'sync-queue'): Promise<boolean> {
  if (!('serviceWorker' in navigator)) return false;

  try {
    const registration = await navigator.serviceWorker.ready;

    if ('sync' in registration) {
      await (registration as any).sync.register(tag);
      console.log('[Sync] Background sync registered:', tag);
      return true;
    }
  } catch (error) {
    console.error('[Sync] Background sync registration failed:', error);
  }

  return false;
}
