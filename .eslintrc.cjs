module.exports = {
  root: true,
  ignorePatterns: [
    'node_modules/',
    'dist/',
    'orchestrator/dist/',
    'build/',
    'coverage/',
    'platform/data/',
    'platform/dashboard/backend/venv/',
    'platform/**/__pycache__/'
  ],
  overrides: [
    {
      files: ['platform/scrapers/**/*.js'],
      env: {
        es2023: true,
        node: true,
        browser: true
      },
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module'
      },
      extends: ['eslint:recommended', 'eslint-config-prettier'],
      rules: {
        'no-console': 'off',
        'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }]
      }
    },
    {
      files: ['platform/dashboard/frontend/**/*.{ts,tsx}'],
      env: {
        browser: true,
        es2023: true
      },
      parser: '@typescript-eslint/parser',
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true
        }
      },
      plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
      extends: [
        'eslint:recommended',
        'plugin:@typescript-eslint/recommended',
        'plugin:react-hooks/recommended',
        'eslint-config-prettier'
      ],
      rules: {
        '@typescript-eslint/consistent-type-imports': 'error',
        'react-refresh/only-export-components': ['warn', { allowConstantExport: true }]
      }
    },
    {
      files: ['orchestrator/**/*.ts'],
      env: {
        es2023: true,
        node: true
      },
      parser: '@typescript-eslint/parser',
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: './orchestrator/tsconfig.json',
        tsconfigRootDir: __dirname
      },
      plugins: ['@typescript-eslint'],
      extends: [
        'eslint:recommended',
        'plugin:@typescript-eslint/recommended',
        'eslint-config-prettier'
      ],
      rules: {
        '@typescript-eslint/consistent-type-imports': 'error',
        '@typescript-eslint/no-non-null-assertion': 'off'
      }
    }
  ]
};
