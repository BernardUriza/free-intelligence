/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  experimental: { externalDir: true },
  typescript: { ignoreBuildErrors: false },
};

module.exports = nextConfig;
