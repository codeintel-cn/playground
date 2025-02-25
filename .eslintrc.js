module.exports = {
  env: {
    browser: false,
    es2021: true,
    mocha: true,
    node: true,
  },
  plugins: ["@typescript-eslint"],
  extends: [
    "standard",
    "plugin:prettier/recommended",
    "plugin:node/recommended",
    "plugin:monorepo/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2021,
  },
  rules: {
    "node/no-unsupported-features/es-syntax": [
      "error",
      { ignores: ["modules"] },
    ],
    "node/no-extraneous-import": "off",
    "node/no-unpublished-require": "off",
    "node/no-unpublished-import": "off",
    "node/no-missing-import": "off",
    "node/no-missing-require": "off",
    "no-unused-expressions": "off",
  },
};
