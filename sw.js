// Offline support: precache the app, then serve from cache and refresh in the background
// (stale-while-revalidate), so updates pushed to GitHub Pages arrive on the next launch.
const CACHE = 'via-latina-v2';
const SHELL = [
  './', 'index.html', 'manifest.webmanifest', 'css/app.css',
  'js/app.js', 'js/art.js', 'js/content.js', 'js/crypto.js', 'js/map.js', 'js/review.js', 'js/state.js', 'js/store.js', 'js/util.js',
  'content.enc', 'assets/assets.json', 'icons/icon-180.png', 'icons/icon-192.png', 'icons/icon-512.png',
];

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await c.addAll(SHELL);
    try { // every art file listed in the manifest
      const m = await (await fetch('assets/assets.json', { cache: 'no-cache' })).json();
      await c.addAll(Object.values(m.assets).map(a => new URL('assets/' + a.file, self.registration.scope).href));
    } catch (err) { /* art will be cached on first use */ }
    self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  const isNav = req.mode === 'navigate';
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    const key = isNav ? new URL('index.html', self.registration.scope).href : req;
    const cached = await c.match(key, { ignoreSearch: true });
    const network = fetch(req, { cache: 'no-cache' }).then(r => {
      if (r && r.ok) c.put(key, r.clone());
      return r;
    }).catch(() => null);
    if (cached) { e.waitUntil(network); return cached; }
    const r = await network;
    return r || new Response('Offline', { status: 503 });
  })());
});
