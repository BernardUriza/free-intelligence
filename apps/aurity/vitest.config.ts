/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['**/__tests__/**/*.{spec,test}.{ts,tsx}', '**/*.{spec,test}.{ts,tsx}'],
    exclude: ['**/node_modules/**', '**/dist/**', '**/out/**', '**/.next/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json', 'json-summary'],
      include: [
        'lib/audio/Error*.ts',
      ],
      exclude: [
        'lib/audio/**/__tests__/**',
        'lib/audio/**/types/**',
        'lib/audio/**/*.test.ts',
        'lib/audio/**/*.spec.ts',
        'lib/audio/ErrorPolicy.ts', // Legacy code mixed with new code
        'lib/audio/AudioStateMachine.ts',
        'lib/audio/CapabilityProbe.ts',
        'lib/audio/QueueManager.ts',
        'lib/audio/ProviderRegistry.ts',
        'lib/audio/constants.ts',
        'lib/audio/formatting.ts',
      ],
      thresholds: {
        lines: 75,
        functions: 75,
        branches: 70,
        statements: 75,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
      '@aurity-standalone/auth': path.resolve(__dirname, './node_modules/@aurity-standalone/auth'),
      '@aurity-standalone/observability': path.resolve(__dirname, './node_modules/@aurity-standalone/observability'),
    },
  },
});
