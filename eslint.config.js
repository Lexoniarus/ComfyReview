import eslint from "@eslint/js";
import globals from "globals";

export default [
  {
    ignores: ["coverage/**", "node_modules/**"],
  },
  eslint.configs.recommended,
  {
    files: ["static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2024,
      globals: globals.browser,
      sourceType: "module",
    },
    rules: {
      "no-console": "error",
    },
  },
  {
    files: ["frontend-tests/**/*.js", "*.config.js"],
    languageOptions: {
      ecmaVersion: 2024,
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      sourceType: "module",
    },
  },
];
