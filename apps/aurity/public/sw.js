// =============================================================================
// AURITY PWA - Service Worker
// =============================================================================
// Provides offline support and caching for the PWA
// Version: 2.0.0 - Modern Architecture
// =============================================================================

const CACHE_VERSION = 'v2';
const STATIC_CACHE = `aurity-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `aurity-dynamic-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline.html';

// Assets to cache on install (App Shell)
const STATIC_ASSETS = [
  '/',
  '/chat/',
  '/dashboard/',
  '/offline.html',
  '/manifest.json',
  '/favicon.png',
  '/icons/icon-192x192.svg',
  '/icons/icon-512x512.svg',
];

// Cache size limits
const DYNAMIC_CACHE_LIMIT = 50;

// Trim cache to limit
async function trimCache(cacheName, maxItems) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length > maxItems) {
    await cache.delete(keys[0]);
    trimCache(cacheName, maxItems);
  }
}

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');

  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching app shell...');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] App shell cached successfully');
        // Don't skip waiting automatically - let the app control updates
      })
      .catch((error) => {
        console.error('[SW] Failed to cache app shell:', error);
      })
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              // Delete caches that don't match current version
              return cacheName.startsWith('aurity-') &&
                     !cacheName.includes(CACHE_VERSION);
            })
            .map((cacheName) => {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service Worker activated');
        return self.clients.claim();
      })
  );
});

// Message handler - for controlled updates from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('[SW] Skip waiting requested');
    self.skipWaiting();
  }
});

// Fetch event - implements different strategies per resource type
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip cross-origin requests
  if (url.origin !== location.origin) {
    return;
  }

  // Skip API requests - always go to network
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // STRATEGY: Network First for navigation (HTML pages)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(DYNAMIC_CACHE).then((cache) => {
            cache.put(request, responseClone);
          });
          return response;
        })
        .catch(() => {
          return caches.match(request)
            .then((cachedResponse) => {
              if (cachedResponse) return cachedResponse;
              return caches.match(OFFLINE_URL);
            });
        })
    );
    return;
  }

  // STRATEGY: Stale While Revalidate for static assets
  if (
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'image' ||
    request.destination === 'font'
  ) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          const fetchPromise = fetch(request)
            .then((networkResponse) => {
              caches.open(STATIC_CACHE).then((cache) => {
                cache.put(request, networkResponse.clone());
              });
              return networkResponse;
            })
            .catch(() => cachedResponse);

          return cachedResponse || fetchPromise;
        })
    );
    return;
  }

  // STRATEGY: Network First with cache fallback (default)
  event.respondWith(
    fetch(request)
      .then((response) => {
        const responseClone = response.clone();
        caches.open(DYNAMIC_CACHE).then((cache) => {
          cache.put(request, responseClone);
          trimCache(DYNAMIC_CACHE, DYNAMIC_CACHE_LIMIT);
        });
        return response;
      })
      .catch(() => caches.match(request))
  );
});

// Handle push notifications (for future use)
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body || 'Nueva notificacion de AURITY',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        url: data.url || '/chat/',
      },
      actions: [
        { action: 'open', title: 'Abrir' },
        { action: 'close', title: 'Cerrar' },
      ],
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'AURITY', options)
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked');
  event.notification.close();

  if (event.action === 'close') {
    return;
  }

  const urlToOpen = event.notification.data?.url || '/chat/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Check if there's already a window/tab open
        for (const client of clientList) {
          if (client.url.includes(urlToOpen) && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window if none found
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Background sync for offline message queue (future use)
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync event:', event.tag);

  if (event.tag === 'sync-messages') {
    event.waitUntil(syncOfflineMessages());
  }
});

// Sync offline messages when back online
async function syncOfflineMessages() {
  console.log('[SW] Syncing offline messages...');
  // Implementation for syncing queued messages
  // This will be triggered when the device comes back online
}

// Periodic sync for background updates (future use)
self.addEventListener('periodicsync', (event) => {
  console.log('[SW] Periodic sync event:', event.tag);

  if (event.tag === 'update-content') {
    event.waitUntil(updateCachedContent());
  }
});

// Update cached content periodically
async function updateCachedContent() {
  console.log('[SW] Updating cached content...');
  const cache = await caches.open(CACHE_NAME);

  // Re-fetch and cache important pages
  const urls = ['/', '/chat/', '/dashboard/'];

  for (const url of urls) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        await cache.put(url, response);
      }
    } catch (error) {
      console.error('[SW] Failed to update cache for:', url, error);
    }
  }
}

console.log('[SW] Service Worker loaded');
