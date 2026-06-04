import { defineConfig } from 'tsup';

// @free-intelligence/core is the material-agnostic substrate layer: contracts
// (theme tokens, voice adapter, chat hook, agent event contract). Pure TS, no
// 'use client' (no components), React only referenced for types. Single ESM entry
// + .d.ts; react is external so the consumer's copy is used.
export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm'],
  dts: true,
  splitting: false,
  treeshake: false,
  sourcemap: true,
  clean: true,
  external: ['react', 'react-dom'],
});
