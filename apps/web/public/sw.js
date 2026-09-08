// Cache only the public offline screen. Never cache auth, API, MCP or finance data.
const CACHE = 'mozhna-public-offline-v2';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.add('/offline.html')));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('mozhna-public-offline-') && key !== CACHE)
      .map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || event.request.mode !== 'navigate' ||
      url.origin !== self.location.origin || url.pathname !== '/') return;
  const offline = async () => {
    const cache = await caches.open(CACHE);
    const saved = await cache.match('/offline.html');
    // Return a fresh navigation response, without the cached resource's URL.
    return saved ? new Response(await saved.arrayBuffer(), {
      status: 200, headers: saved.headers,
    }) : Response.error();
  };
  // Avoid starting a navigation fetch when the browser already reports offline.
  // A network failure while navigator.onLine is true still uses the same screen.
  event.respondWith(self.navigator.onLine === false
    ? offline() : fetch(event.request).catch(offline));
});
