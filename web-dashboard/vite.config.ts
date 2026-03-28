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
  build: {
    outDir: "assets",
    emptyOutDir: false,
    rollupOptions: {
      input: path.resolve(__dirname, "src/beams-mount.tsx"),
      output: {
        inlineDynamicImports: true,
        entryFileNames: "beams-bg.js",
        assetFileNames: "beams-bg[extname]",
      },
    },
  },
});
