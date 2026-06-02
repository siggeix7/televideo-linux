const CACHE_NAME = "televideo-v10";
const STATIC_ASSETS = [
    "/",
    "/static/news/styles.css",
    "/static/news/app.js",
    "/static/news/superenalotto.js",
    "/static/news/storico_estrazioni.js",
    "/static/news/storico_montepremi.js",
    "/static/news/fanta_super.js",
    "/feed.xml",
];

function cacheCopy(request, response) {
    if (!response || !response.ok) return response;
    const clone = response.clone();
    caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
    return response;
}

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    if (url.pathname.startsWith("/api/")) {
        return;
    }

    if (event.request.method !== "GET") {
        return;
    }

    const sameOrigin = url.origin === self.location.origin;
    const acceptsHtml = event.request.headers.get("Accept")?.includes("text/html");

    if (event.request.mode === "navigate" || acceptsHtml) {
        event.respondWith(
            fetch(event.request)
                .then((response) => sameOrigin ? cacheCopy(event.request, response) : response)
                .catch(() => caches.match(event.request).then((cached) => cached || caches.match("/") || new Response("Offline", { status: 503 })))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cached) => {
            const network = fetch(event.request)
                .then((response) => sameOrigin ? cacheCopy(event.request, response) : response)
                .catch(() => cached || new Response("Offline", { status: 503 }));

            return cached || network;
        })
    );
});
