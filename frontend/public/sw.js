/**
 * Alphha DMS Service Worker
 * Handles offline caching, background sync, and push notifications
 */

const CACHE_NAME = 'alphha-dms-v1';
const STATIC_CACHE = 'alphha-static-v1';
const API_CACHE = 'alphha-api-v1';
const DOCUMENT_CACHE = 'alphha-documents-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/offline.html',
];

// API routes to cache
const API_ROUTES = [
  '/api/v1/auth/me',
  '/api/v1/documents',
  '/api/v1/folders',
  '/api/v1/notifications',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              return name.startsWith('alphha-') &&
                     name !== STATIC_CACHE &&
                     name !== API_CACHE &&
                     name !== DOCUMENT_CACHE;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - handle requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests for caching (but allow sync queue handling)
  if (request.method !== 'GET') {
    // Queue failed mutations for background sync
    if (request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE') {
      event.respondWith(handleMutation(request));
    }
    return;
  }

  // API requests - network first, cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstStrategy(request, API_CACHE));
    return;
  }

  // Document files - cache first for offline access
  if (url.pathname.startsWith('/uploads/') || url.pathname.includes('/download')) {
    event.respondWith(cacheFirstStrategy(request, DOCUMENT_CACHE));
    return;
  }

  // Static assets - cache first
  event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
});

/**
 * Cache-first strategy: Try cache, then network
 */
async function cacheFirstStrategy(request, cacheName) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // Refresh cache in background
    fetchAndCache(request, cacheName);
    return cachedResponse;
  }

  return fetchAndCache(request, cacheName);
}

/**
 * Network-first strategy: Try network, cache fallback
 */
async function networkFirstStrategy(request, cacheName) {
  try {
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);

    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }

    // Return error response for API requests
    return new Response(
      JSON.stringify({ error: 'Offline', message: 'Network unavailable' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Fetch and cache a request
 */
async function fetchAndCache(request, cacheName) {
  try {
    const response = await fetch(request);

    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log('[SW] Fetch failed:', request.url);
    throw error;
  }
}

/**
 * Handle mutation requests (POST, PUT, DELETE)
 * Queue for background sync if offline
 */
async function handleMutation(request) {
  try {
    const response = await fetch(request.clone());
    return response;
  } catch (error) {
    // Queue for background sync
    const serialized = await serializeRequest(request);
    await queueForSync(serialized);

    return new Response(
      JSON.stringify({
        queued: true,
        message: 'Request queued for sync'
      }),
      {
        status: 202,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Serialize request for storage
 */
async function serializeRequest(request) {
  const body = await request.text();
  return {
    url: request.url,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body: body,
    timestamp: Date.now()
  };
}

/**
 * Queue request for background sync
 */
async function queueForSync(serializedRequest) {
  const db = await openSyncDB();
  const tx = db.transaction('syncQueue', 'readwrite');
  const store = tx.objectStore('syncQueue');

  await store.add({
    id: `sync-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    request: serializedRequest,
    status: 'pending',
    retries: 0
  });

  // Register for background sync
  if ('sync' in self.registration) {
    await self.registration.sync.register('sync-mutations');
  }
}

/**
 * Open IndexedDB for sync queue
 */
function openSyncDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('alphha-sync', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('syncQueue')) {
        db.createObjectStore('syncQueue', { keyPath: 'id' });
      }
    };
  });
}

// Background sync event
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-mutations') {
    event.waitUntil(processSyncQueue());
  }
});

/**
 * Process queued requests
 */
async function processSyncQueue() {
  const db = await openSyncDB();
  const tx = db.transaction('syncQueue', 'readwrite');
  const store = tx.objectStore('syncQueue');

  const items = await new Promise((resolve, reject) => {
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });

  for (const item of items) {
    if (item.status !== 'pending') continue;

    try {
      const { request: serialized } = item;

      const response = await fetch(serialized.url, {
        method: serialized.method,
        headers: serialized.headers,
        body: serialized.body || undefined
      });

      if (response.ok) {
        // Remove from queue on success
        await store.delete(item.id);

        // Notify clients
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
          client.postMessage({
            type: 'SYNC_SUCCESS',
            request: serialized
          });
        });
      } else if (item.retries < 3) {
        // Retry later
        item.retries++;
        item.status = 'pending';
        await store.put(item);
      } else {
        // Max retries reached, mark as failed
        item.status = 'failed';
        await store.put(item);
      }
    } catch (error) {
      console.error('[SW] Sync failed for item:', item.id, error);
      item.retries++;
      await store.put(item);
    }
  }
}

// Push notification event
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  let data = { title: 'Alphha DMS', body: 'You have a new notification' };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      url: data.url || '/'
    },
    actions: data.actions || [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);

  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window if available
        for (const client of clientList) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window
        if (self.clients.openWindow) {
          return self.clients.openWindow(urlToOpen);
        }
      })
  );
});

// Message event - handle messages from clients
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  const { type, payload } = event.data;

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CACHE_DOCUMENT':
      cacheDocument(payload.documentId, payload.url);
      break;

    case 'REMOVE_DOCUMENT':
      removeFromCache(payload.documentId);
      break;

    case 'GET_SYNC_STATUS':
      getSyncStatus().then(status => {
        event.ports[0].postMessage(status);
      });
      break;

    case 'CLEAR_CACHE':
      clearAllCaches().then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;
  }
});

/**
 * Cache a document for offline access
 */
async function cacheDocument(documentId, url) {
  try {
    const cache = await caches.open(DOCUMENT_CACHE);
    const response = await fetch(url);

    if (response.ok) {
      await cache.put(url, response);
      console.log('[SW] Document cached:', documentId);

      // Notify clients
      const clients = await self.clients.matchAll();
      clients.forEach(client => {
        client.postMessage({
          type: 'DOCUMENT_CACHED',
          documentId
        });
      });
    }
  } catch (error) {
    console.error('[SW] Failed to cache document:', error);
  }
}

/**
 * Remove document from cache
 */
async function removeFromCache(documentId) {
  const cache = await caches.open(DOCUMENT_CACHE);
  const keys = await cache.keys();

  for (const request of keys) {
    if (request.url.includes(documentId)) {
      await cache.delete(request);
      console.log('[SW] Document removed from cache:', documentId);
    }
  }
}

/**
 * Get sync queue status
 */
async function getSyncStatus() {
  try {
    const db = await openSyncDB();
    const tx = db.transaction('syncQueue', 'readonly');
    const store = tx.objectStore('syncQueue');

    const items = await new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    return {
      pending: items.filter(i => i.status === 'pending').length,
      failed: items.filter(i => i.status === 'failed').length,
      total: items.length
    };
  } catch (error) {
    return { pending: 0, failed: 0, total: 0 };
  }
}

/**
 * Clear all caches
 */
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(
    cacheNames
      .filter(name => name.startsWith('alphha-'))
      .map(name => caches.delete(name))
  );
}
