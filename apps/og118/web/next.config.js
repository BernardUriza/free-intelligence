/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Static export → deploys to the og118.ai SWA (same target as the landing it replaces).
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,

  // Allow importing fi-glass / @free-intelligence/core BUILT dist from the
  // monorepo (outside this app's dir). They ship pre-compiled — NOT transpiled
  // here. This is og118 consuming the v1 release artifact, the "1 build → N
  // consumers" thesis, from a fresh app (not aurity).
  experimental: { externalDir: true },
  transpilePackages: ['recordrtc'],

  typescript: { ignoreBuildErrors: false },
};

module.exports = nextConfig;
