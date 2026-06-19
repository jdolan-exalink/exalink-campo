// App Shell Service Worker — cache-first for static assets, network-only for API
const CACHE = 'exalink-campo-v1'
const OFFLINE_URL = '/'

const STATIC_EXTENSIONS = ['.js', '.css', '.woff2', '.woff', '.png', '.svg', '.ico']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll([OFFLINE_URL]))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Pass through API and non-GET requests
  if (request.method !== 'GET') return
  if (url.pathname.startsWith('/api')) return

  // Navigation: serve index.html (SPA shell)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_URL).then(r => r || Response.error())
      )
    )
    return
  }

  // Static assets: cache-first, then network + cache
  const isStatic = STATIC_EXTENSIONS.some(ext => url.pathname.endsWith(ext))
  if (isStatic) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached
        return fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone()
            caches.open(CACHE).then(cache => cache.put(request, clone))
          }
          return response
        })
      })
    )
  }
})
