const CACHE_NAME = 'chikguard-v3';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const { request } = e;
  const url = new URL(request.url);

  // 1. Ignora completamente requests cross-origin (ex: 127.0.0.1:5000, supabase.co)
  //    Deixa o browser lidar diretamente — SW não interfere.
  if (url.origin !== self.location.origin) {
    return; // NÃO chame e.respondWith() — passa direto pro browser
  }

  // 2. Ignora requisições que não são GET
  if (request.method !== 'GET') {
    return;
  }

  // 3. Para index.html: Network-First (evita carregar hashes antigos do JS)
  if (url.pathname === '/' || url.pathname === '/index.html') {
    e.respondWith(
      fetch(request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // 4. Para assets estáticos do próprio origin: Cache-First
  e.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((res) => {
        // Só cacheia responses válidas de assets estáticos
        if (res && res.status === 200 && res.type === 'basic') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return res;
      });
    })
  );
});
