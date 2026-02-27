// static/miniapp/sw.js
// Service Worker for PWA functionality

const CACHE_NAME = 'dod-miniapp-v1.0.0';
const STATIC_CACHE = 'dod-static-v1.0.0';
const API_CACHE = 'dod-api-v1.0.0';

// Files to cache immediately
const STATIC_FILES = [
  '/',
  '/tg/',
  '/static/miniapp/css/miniapp.css',
  '/static/miniapp/js/app.js',
  '/static/miniapp/js/telegram.js',
  '/static/miniapp/manifest.json',
  '/static/miniapp/img/icon-192.png',
  '/static/miniapp/img/icon-512.png',
  // Add other static assets
];

// API endpoints that can be cached (read-only)
const CACHEABLE_APIS = [
  '/tg/api/live-matches/',
];

// Install event - cache static files
self.addEventListener('install', event => {
  console.log('Service Worker installing.');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        return self.skipWaiting();
      })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  console.log('Service Worker activating.');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== API_CACHE && cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Fetch event - handle requests
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Handle API requests
  if (url.pathname.startsWith('/tg/api/')) {
    event.respondWith(handleApiRequest(event.request));
    return;
  }

  // Handle static assets
  if (url.pathname.startsWith('/static/') ||
      url.pathname.includes('.css') ||
      url.pathname.includes('.js') ||
      url.pathname.includes('.png') ||
      url.pathname.includes('.jpg') ||
      url.pathname.includes('.svg')) {
    event.respondWith(handleStaticRequest(event.request));
    return;
  }

  // Handle navigation requests
  if (event.request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(event.request));
    return;
  }

  // Default - network first for dynamic content
  event.respondWith(
    fetch(event.request)
      .catch(() => {
        // Offline fallback
        if (event.request.destination === 'document') {
          return caches.match('/offline.html');
        }
        return new Response('Offline', { status: 503 });
      })
  );
});

// Handle API requests
async function handleApiRequest(request) {
  const url = new URL(request.url);

  // Cache read-only APIs
  if (CACHEABLE_APIS.some(api => url.pathname.includes(api))) {
    const cache = await caches.open(API_CACHE);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      // Return cached version and update in background
      fetch(request).then(response => {
        if (response.ok) {
          cache.put(request, response.clone());
        }
      });
      return cachedResponse;
    }

    // Fetch and cache
    try {
      const response = await fetch(request);
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    } catch (error) {
      return new Response(JSON.stringify({ error: 'Offline' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }

  // Network only for write operations
  try {
    return await fetch(request);
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Network error' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Handle static requests
async function handleStaticRequest(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.log('Failed to fetch static asset:', request.url);
    return new Response('', { status: 404 });
  }
}

// Handle navigation requests
async function handleNavigationRequest(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cachedResponse = await cache.match('/tg/');

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    return await fetch(request);
  } catch (error) {
    // Return offline page
    const offlineResponse = await cache.match('/offline.html');
    if (offlineResponse) {
      return offlineResponse;
    }

    // Fallback offline page
    return new Response(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>DOD - Offline</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1a1a2e;
            color: #ffffff;
            text-align: center;
            padding: 50px 20px;
          }
          .icon { font-size: 4rem; margin-bottom: 1rem; }
          h1 { margin-bottom: 1rem; }
          p { opacity: 0.8; }
        </style>
      </head>
      <body>
        <div class="icon">📱</div>
        <h1>Нет подключения</h1>
        <p>Проверьте интернет-соединение и попробуйте снова</p>
      </body>
      </html>
    `, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

// Background sync for failed requests
self.addEventListener('sync', event => {
  console.log('Background sync triggered:', event.tag);

  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

// Push notifications
self.addEventListener('push', event => {
  console.log('Push message received:', event);

  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/static/miniapp/img/icon-192.png',
      badge: '/static/miniapp/img/icon-192.png',
      data: data.data || {},
      actions: data.actions || []
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'DOD', options)
    );
  }
});

// Notification click
self.addEventListener('notificationclick', event => {
  console.log('Notification clicked:', event);
  event.notification.close();

  const data = event.notification.data;

  if (data && data.url) {
    event.waitUntil(
      clients.openWindow(data.url)
    );
  } else {
    event.waitUntil(
      clients.openWindow('/tg/')
    );
  }
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', event => {
  console.log('Periodic sync triggered:', event.tag);

  if (event.tag === 'update-content') {
    event.waitUntil(updateContent());
  }
});

// Helper functions
async function doBackgroundSync() {
  console.log('Performing background sync...');
  // Retry failed requests, update content, etc.
}

async function updateContent() {
  console.log('Updating content in background...');
  // Update cached API data, check for new content, etc.
}

// Message from main thread
self.addEventListener('message', event => {
  console.log('Message from main thread:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
