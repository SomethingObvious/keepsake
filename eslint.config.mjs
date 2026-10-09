// The window's linter, at the strictest setting each plugin offers, as in
// afterimage's desktop app.
//
// Type-checked rules, not the syntactic subset: a floating promise, a value
// narrowed to `any` at the Python boundary, a condition that is always true,
// are all legal JavaScript that `tsc` says nothing about. app.js is plain
// JavaScript checked against ui/types.d.ts, so there is no build step and
// nothing between what is linted and what runs.
//
// Per-line escapes are banned: scripts/lint.py rejects every inline
// suppression in every tracked file, so a disagreement with a rule is written
// down here, with its reason, or not at all.

import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["node_modules/**", "build/**", "dist/**"] },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
  },
  {
    files: ["ui/**/*.js"],
    languageOptions: {
      sourceType: "script",
      globals: { ...globals.browser },
    },
    rules: {
      // A promise nobody waits for is a failure nobody sees, and this window
      // is almost entirely calls across the bridge to Python.
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",
      // An unused variable in a window this size is nearly always a control
      // that was rewired and left half-connected.
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", caughtErrors: "all" }],
      // Core rules the recommended sets leave off, which are cheap and catch
      // real mistakes in hand-written DOM code.
      eqeqeq: ["error", "always"],
      "no-var": "error",
      "prefer-const": "error",
      "no-implicit-coercion": "error",
      "no-shadow": "off",
      "@typescript-eslint/no-shadow": "error",
      "no-param-reassign": "error",
      "no-console": ["error", { allow: ["error"] }],
      curly: ["error", "all"],
      "no-else-return": "error",
      "no-lonely-if": "error",
      "no-useless-return": "error",
      "object-shorthand": "error",
      "prefer-template": "error",
      "no-nested-ternary": "off",
    },
  },
  {
    // The linter's own configuration: JavaScript in no tsconfig, so the
    // type-aware rules have no program to ask; the syntax rules still apply.
    files: ["eslint.config.mjs"],
    extends: [tseslint.configs.disableTypeChecked],
  },
);
