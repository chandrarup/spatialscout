import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies /api to the FastAPI app (`make api`, or both at once with `make dev`), so the web app
// always talks to one origin. SPATIALSCOUT_API_PORT picks the API's port (default 8000).
const apiPort = process.env.SPATIALSCOUT_API_PORT ?? "8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { "/api": { target: `http://127.0.0.1:${apiPort}`, changeOrigin: false } },
  },
  // deck.gl alone is about 900 kB minified; one chunk is fine for this app.
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 1200 },
});
