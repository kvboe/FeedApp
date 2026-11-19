/* FeedApp service worker: app-shell caching, API always goes to network.
 * __BUILD_ID__ is replaced at build time (vite.config.ts), so every deploy gets
 * a fresh cache and the previous build's assets are evicted on activate. */
const CACHE = "feedapp-__BUILD_ID__";
const SHELL = ["/", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

/** Only successful, same-origin, non-redirected responses are worth keeping. */
function cacheable(res) {
  return res && res.ok && res.type === "basic" && !res.redirected;
}

function put(key, res) {
  if (!cacheable(res)) return;
  const copy = res.clone();
  caches.open(CACHE).then((c) => c.put(key, copy));
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;

  // Navigations: network first; a successful HTML response refreshes the shell.
  // Error pages (e.g. 503 mid-deploy) are passed through but never cached.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if ((res.headers.get("content-type") || "").includes("text/html")) put("/", res);
          return res;
        })
        .catch(() => caches.match("/").then((hit) => hit || Response.error())),
    );
    return;
  }

  // Content-hashed build assets never change: cache first.
  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((res) => {
            put(request, res);
            return res;
          }),
      ),
    );
    return;
  }

  // Everything else (manifest, icons): network first so updates arrive, cache offline.
  event.respondWith(
    fetch(request)
      .then((res) => {
        put(request, res);
        return res;
      })
      .catch(() => caches.match(request).then((hit) => hit || Response.error())),
  );
});
