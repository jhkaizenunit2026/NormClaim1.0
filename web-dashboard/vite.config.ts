import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  // Dev server serves both index.html and app.html
  // React TSX modules are handled natively by Vite in dev mode
  build: {
    outDir: "assets",
    emptyOutDir: false,
    rollupOptions: {
      input: {
        beams: path.resolve(__dirname, "src/beams-mount.tsx"),
        statcards: path.resolve(__dirname, "src/stat-cards-mount.tsx"),
        auth: path.resolve(__dirname, "src/auth-mount.tsx"),
      },
      output: {
        inlineDynamicImports: false,
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === "beams") return "beams-bg.js";
          if (chunkInfo.name === "statcards") return "stat-cards.js";
          if (chunkInfo.name === "auth") return "auth-overlay.js";
          return "[name].js";
        },
        assetFileNames: "[name][extname]",
      },
    },
  },
});
