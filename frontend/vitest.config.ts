import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    // Playwright specs (e2e/) and the project guide's node:test suite run separately.
    exclude: [...configDefaults.exclude, "e2e/**", "project-guide/**"],
    coverage: {
      reporter: ["text", "html"],
      reportsDirectory: "coverage",
    },
  },
});
