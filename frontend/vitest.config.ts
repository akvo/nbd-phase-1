import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./vitest.setup.ts",
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    coverage: {
      provider: "v8",
      reporter: ["text"],
      reportsDirectory: "node_modules/.cache/coverage",
      exclude: [
        "node_modules/**",
        ".next/**",
        "next.config.ts",
        "postcss.config.mjs",
        "next-env.d.ts",
      ],
    },
  },
});
