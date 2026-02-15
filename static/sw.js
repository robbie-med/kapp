const CACHE_NAME = 'korean-app-v2';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/api.js',
    '/static/js/audio.js',
    '/static/js/app.js',
    '/static/js/components/feedback.js',
    '/static/js/components/item-card.js',
    '/static/js/components/nav.js',
    '/static/js/pages/practice.js',
    '/static/js/pages/review.js',
    '/static/js/pages/items.js',
    '/static/js/pages/stats.js',
    '/static/js/pages/settings.js',
    '/static/js/pages/teacher.js',
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url);

    // Network-first for API calls
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // Cache-first for static assets
    e.respondWith(
        caches.match(e.request).then(cached => {
            if (cached) return cached;
            return fetch(e.request).then(response => {
                if (response.ok && url.pathname.startsWith('/static/')) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
                }
                return response;
            });
        }).catch(() => {
            if (e.request.mode === 'navigate') {
                return caches.match('/');
            }
        })
    );
});
