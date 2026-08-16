/* Map for Women service worker.
 *
 * Honest caching policy:
 *  - Cache ONLY static assets (hashed Next.js build output, fonts, icons).
 *  - NEVER cache /api/ responses: safety evidence and route risk must always
 *    come from the backend; serving stale safety data would be dishonest.
 *  - OSM tile fetches are left untouched: without connectivity they fail
 *    gracefully (the map already has a no-tiles fallback).
 */
const STATIC_CACHE = "mf-static-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(STATIC_CACHE));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== STATIC_CACHE).map((k) => caches.delete(k))),
      ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  const request = event.request;

  if (request.method !== "GET") return;

  // Static, hashed build assets: cache-first, populate on first visit.
  if (
    url.pathname.startsWith("/_next/") ||
    url.pathname.startsWith("/fonts/") ||
    url.pathname === "/icon.svg" ||
    url.pathname === "/icon-maskable.svg"
  ) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone));
            }
            return response;
          }),
      ),
    );
    return;
  }

  // Document navigations: network-first with a static fallback so the app
  // shell stays reachable offline. The shell itself never shows stale safety
  // data — it shows the offline banner and waits for the API.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put("/", clone));
          }
          return response;
        })
        .catch(() => caches.match("/")),
    );
  }
});
