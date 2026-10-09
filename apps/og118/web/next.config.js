const { execSync } = require('node:child_process');

function git(args) {
  try {
    return execSync(`git ${args}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch {
    return '';
  }
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Sidebar release line: the deployed commit and when it landed on main.
  env: {
    NEXT_PUBLIC_OG118_RELEASE_SHA: process.env.GITHUB_SHA || git('rev-parse HEAD'),
    NEXT_PUBLIC_OG118_RELEASED_AT: git('log -1 --format=%cI'),
  },

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
