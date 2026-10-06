import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon-180x180.png', 'logo.svg'],
      manifest: {
        name: 'Clipo',
        short_name: 'Clipo',
        description: 'Descarga videos de cualquier plataforma con yt-dlp',
        lang: 'es',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        theme_color: '#1b1a19',
        background_color: '#1b1a19',
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2,webmanifest}'],
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//, /^\/diag\.html/],
        cleanupOutdatedCaches: true,
        // /file va directo a la red: un video de varios GB no debe pasar por el service worker
        runtimeCaching: [{ urlPattern: ({ url }) => url.pathname.startsWith('/api/') && !url.pathname.endsWith('/file'), handler: 'NetworkOnly' }],
      },
    }),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: { environment: 'node' },
})
