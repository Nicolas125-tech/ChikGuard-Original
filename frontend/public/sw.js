const CACHE_NAME = 'chikguard-v2';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) return caches.delete(k);
        })
      );
    })
  );
});

// Cache-First strategy for static assets, Network-First for API and index.html (to prevent stale hashes)
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  if (url.pathname.includes('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
  } else if (url.pathname === '/' || url.pathname === '/index.html') {
    // Network-First for the index.html to avoid loading deleted hashes (404 index-XXXX.js)
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
  } else {
    e.respondWith(
      caches.match(e.request).then((res) => res || fetch(e.request))
    );
  }
});
