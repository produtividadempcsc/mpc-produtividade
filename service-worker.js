// Service Worker - MPC-SC Produtividade
// Estratégia: Network-first com fallback para cache

const CACHE_NAME = 'mpcsc-produtividade-v1';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/logo_mpcsc.jpg'
];

// Instalação: cachear recursos estáticos essenciais
self.addEventListener('install', (event) => {
    console.log('[SW] Instalando Service Worker...');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Ativação: limpar caches antigos
self.addEventListener('activate', (event) => {
    console.log('[SW] Service Worker ativado');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// Fetch: network-first para dados dinâmicos, cache-first para estáticos
self.addEventListener('fetch', (event) => {
    // Ignorar requisições não-GET
    if (event.request.method !== 'GET') return;

    // Para recursos estáticos conhecidos, usar cache-first
    const url = new URL(event.request.url);
    const isStatic = STATIC_ASSETS.some(asset => url.pathname.endsWith(asset));

    if (isStatic) {
        event.respondWith(
            caches.match(event.request).then((cached) => {
                return cached || fetch(event.request).then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    return response;
                });
            })
        );
    } else {
        // Para todo o resto, network-first
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    return response;
                })
                .catch(() => {
                    return caches.match(event.request);
                })
        );
    }
});
