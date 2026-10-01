import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const root = path.dirname(fileURLToPath(import.meta.url));
const coreScope = fs
  .readFileSync(path.join(root, "quality/frontend_core_scope.txt"), "utf8")
  .split(/\r?\n/u)
  .map((line) => line.trim())
  .filter((line) => line && !line.startsWith("#"));

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["frontend-tests/**/*.test.js"],
    coverage: {
      include: coreScope,
      provider: "v8",
      reporter: ["text", "json-summary"],
      reportsDirectory: "coverage/frontend",
      thresholds: {
        functions: 100,
        statements: 100,
      },
    },
  },
});
