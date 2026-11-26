import vue from "@vitejs/plugin-vue";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "apple-touch-icon-180x180.png"],
      manifest: {
        name: "Overloader",
        short_name: "Overloader",
        description: "Log your lifts and watch progressive overload add up.",
        theme_color: "#14161a",
        background_color: "#14161a",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "pwa-64x64.png", sizes: "64x64", type: "image/png" },
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "maskable-icon-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            // The exercise catalog rarely changes, so it can load from cache in a dead-zone gym.
            urlPattern: ({ url }) => url.pathname === "/api/exercises",
            handler: "StaleWhileRevalidate",
            options: { cacheName: "catalog" },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5180,
    strictPort: true,
    // The API runs on :8000 in dev; proxying keeps it same-origin, so no CORS setup is needed.
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  test: { environment: "node" },
});
