import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/** Stamp a unique build id into dist/sw.js so each deploy gets its own cache. */
function swBuildId(): Plugin {
  let outDir = "dist";
  return {
    name: "sw-build-id",
    apply: "build",
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir);
    },
    closeBundle() {
      const file = resolve(outDir, "sw.js");
      const id = Date.now().toString(36);
      writeFileSync(file, readFileSync(file, "utf8").replaceAll("__BUILD_ID__", id));
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), swBuildId()],
  server: {
    host: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { target: "es2022" },
});
