/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [],
    // Exclude Playwright E2E tests — they run separately via `test:e2e`
    exclude: ['tests/e2e/**', 'node_modules/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      // Pareto principle: only measure the 20% that matters most
      // (React Flow Custom Nodes/Edges — the core UI business logic).
      // App.tsx, hooks and layout components are covered by the E2E suite.
      include: [
        'src/components/CustomNode.tsx',
        'src/components/CustomEdge.tsx',
      ],
      // Gate: 100% for the Pareto core components
      thresholds: {
        lines: 100,
        functions: 100,
        branches: 80,
        statements: 100,
      },
    },
  },
})
