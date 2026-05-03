// Minimal flat-config ESLint setup for the HackSim Next.js app.
//
// We deliberately keep this lean. The recommended typescript-eslint rule set
// catches genuine bugs (no-unused-vars, no-explicit-any, no-unused-imports
// etc.) without imposing a style debate. tsc --noEmit catches the type
// errors. vitest catches the behaviour. Project-specific overrides go below
// only when a real rule violation is producing noise that obscures real bugs.

import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      ".next/**",
      "out/**",
      "node_modules/**",
      "coverage/**",
      "tests/**",
      "next-env.d.ts",
      "lib/mocks/projects/**",
      "**/*.config.mjs",
      "**/*.config.js",
      "**/*.config.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      // The codebase uses `_unused` underscore prefix for intentionally
      // unused parameters (callbacks where the framework supplies more
      // arguments than we read). This matches typescript-eslint's default
      // pattern.
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // The `any` type appears in a few well-marked spots (intentional
      // escape hatches with adjacent comments). We allow it but prefer
      // explicit when possible.
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
);
