// Service Worker for Golf Scorecard PWA
const CACHE_NAME = 'golf-scorecard-v1';
const STATIC_CACHE = 'static-v1';

const STATIC_ASSETS = [
    '/',
    '/static/css/styles.css',
    '/static/js/app.js',
    '/static/manifest.json'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(name => name !== CACHE_NAME && name !== STATIC_CACHE)
                        .map(name => caches.delete(name))
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // API requests - network first, then cache
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    // Clone the response for caching
                    const clonedResponse = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => cache.put(request, clonedResponse));
                    return response;
                })
                .catch(() => caches.match(request))
        );
        return;
    }

    // Static assets - cache first, then network
    event.respondWith(
        caches.match(request)
            .then(cachedResponse => {
                if (cachedResponse) {
                    return cachedResponse;
                }

                return fetch(request)
                    .then(response => {
                        // Don't cache non-success responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        const clonedResponse = response.clone();
                        caches.open(STATIC_CACHE)
                            .then(cache => cache.put(request, clonedResponse));

                        return response;
                    });
            })
    );
});

// Handle background sync for offline score submission
self.addEventListener('sync', event => {
    if (event.tag === 'sync-scores') {
        event.waitUntil(syncScores());
    }
});

async function syncScores() {
    // Implement offline score syncing logic here
    console.log('Syncing offline scores...');
}
