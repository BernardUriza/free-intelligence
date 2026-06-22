import { defineConfig } from 'tsup';
import { preserveDirectivesPlugin } from 'esbuild-plugin-preserve-directives';

// fi-glass ships an unbundled ESM build mirroring the src subpaths, plus .d.ts.
// React, the UI libs (peerDependencies) and the core contract are EXTERNAL so the
// consumer's single copy is used (no duplicate react/lucide). 'use client' must
// survive into dist for the RSC boundaries to hold in the consumer — validated by
// a grep gate after the build.
export default defineConfig({
  entry: [
    'src/index.ts',
    'src/theme/index.ts',
    'src/messages/index.ts',
    'src/composer/index.ts',
    'src/voice/index.ts',
    'src/shell/index.ts',
    'src/persona-selector/index.ts',
    'src/agent/index.ts',
    'src/conversation/index.ts',
    'src/identity/index.ts',
  ],
  format: ['esm'],
  dts: { compilerOptions: { skipLibCheck: true } },
  splitting: false,
  treeshake: false,
  sourcemap: true,
  clean: true,
  external: [
    'react',
    'react-dom',
    'lucide-react',
    'framer-motion',
    'react-markdown',
    'remark-gfm',
    'recordrtc',
    '@free-intelligence/core',
  ],
  esbuildPlugins: [
    preserveDirectivesPlugin({
      directives: ['use client', 'use strict'],
      include: /\.(jsx?|tsx?)$/,
      exclude: /node_modules/,
    }),
  ],
});
