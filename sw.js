/* Retired root service worker. BADS moved to /bads/ (its own worker lives at /bads/sw.js).
   Anyone who installed the old root worker gets it removed: clear the old cache, unregister, reload. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k === "bads-v1").map((k) => caches.delete(k)));
    await self.registration.unregister();
    const wins = await self.clients.matchAll({ type: "window" });
    wins.forEach((c) => c.navigate(c.url));
  })());
});
