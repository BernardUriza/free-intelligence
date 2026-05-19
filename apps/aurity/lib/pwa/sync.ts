// =============================================================================
// PWA Background Sync Manager
// =============================================================================
// Handles syncing queued actions when device comes back online
// =============================================================================

import { getQueuedActions, removeQueuedAction, QueuedAction } from './storage';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('Sync');

type SyncHandler = (action: QueuedAction) => Promise<boolean>;

const syncHandlers = new Map<string, SyncHandler>();

/**
 * Register a handler for a specific action type
 */
export function registerSyncHandler(type: string, handler: SyncHandler): void {
  syncHandlers.set(type, handler);
  log.debug('Registered handler', { type });
}

/**
 * Process all queued actions
 */
export async function processQueue(): Promise<{ success: number; failed: number }> {
  const actions = await getQueuedActions();
  let success = 0;
  let failed = 0;

  log.debug('Processing queue', { count: actions.length });

  for (const action of actions) {
    const handler = syncHandlers.get(action.type);

    if (!handler) {
      log.warn('No handler for action type', { type: action.type });
      failed++;
      continue;
    }

    try {
      const result = await handler(action);

      if (result && action.id) {
        await removeQueuedAction(action.id);
        success++;
      } else {
        failed++;
      }
    } catch (error) {
      log.error('Failed to sync action', { type: action.type, error: String(error) });
      failed++;
    }
  }

  log.info('Queue processed', { success, failed });
  return { success, failed };
}

/**
 * Initialize sync manager - listens for online events
 */
export function initSyncManager(): () => void {
  const handleOnline = async () => {
    log.info('Device online, processing queue');
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
      log.debug('Background sync registered', { tag });
      return true;
    }
  } catch (error) {
    log.error('Background sync registration failed', { error: String(error) });
  }

  return false;
}
