const APP_CACHE = 'kiirus-app-v1';
const PYODIDE_CACHE = 'pyodide-immutable';

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(APP_CACHE).then(c => c.addAll(['./index.html']))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k.startsWith('kiirus-app-') && k !== APP_CACHE)
            .map(k => caches.delete(k))
      )
    )
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  // Pyodide and CDN assets — cache forever, never invalidate
  if (url.includes('cdn.jsdelivr.net') ||
      url.includes('pyodide') ||
      url.includes('cdnjs.cloudflare.com')) {
    e.respondWith(
      caches.open(PYODIDE_CACHE).then(cache =>
        cache.match(e.request).then(cached => {
          if (cached) return cached;
          return fetch(e.request).then(res => {
            cache.put(e.request, res.clone());
            return res;
          });
        })
      )
    );
    return;
  }

  // App files — use updated version when available
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
