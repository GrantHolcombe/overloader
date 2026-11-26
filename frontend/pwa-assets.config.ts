import { defineConfig, minimal2023Preset } from "@vite-pwa/assets-generator/config";

// `npm run icons` regenerates the PNG icons in public/ from public/favicon.svg.
export default defineConfig({
  preset: minimal2023Preset,
  images: ["public/favicon.svg"],
});
