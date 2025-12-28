/**
 * Free Intelligence - Next.js Configuration
 * 
 * Configuration for development proxy and production static export
 */

const nextConfig = {
  reactStrictMode: true,

  // STATIC EXPORT MODE - For DigitalOcean Spaces/CDN (PRODUCTION)
  // COMMENT OUT FOR DEVELOPMENT to enable API routes and proxy
  // output: 'export',

  // Images - disabled for static export, enabled for dev
  images: {
    unoptimized: true, // Can't use Next.js Image Optimization in static export
  },

  // Trailing slashes (if needed)
  trailingSlash: false, // Temporarily false for development

  experimental: {
    externalDir: true,
  },

  transpilePackages: [
    '@fi/shared',
    '@aurity/fi-auth',
    '@aurity/fi-observability',
    'recordrtc',
  ],

  typescript: {
    ignoreBuildErrors: true,
  },

  // Proxy configuration for development
  async rewrites() {
    // Only enable the internal proxy in development to avoid accidental exposure
    const rewrites = [
      // Proxy API requests to backend
      {
        source: '/api/:path*',
        destination: 'http://localhost:7001/api/:path*', // FI backend
      },
      {
        source: '/health',
        destination: 'http://localhost:7001/health', // Health check
      },
    ];

    if (process.env.NODE_ENV !== 'production') {
      rewrites.push({
        source: '/internal/:path*',
        destination: 'http://localhost:7001/internal/:path*', // FI internal API (dev only)
      });
    }

    return rewrites;
  },
  
  turbopack: {},
};

// Conditionally disable static export for development
if (process.env.NODE_ENV !== 'production') {
  // Remove static export for development to enable server-side features
  delete nextConfig.output;
  nextConfig.trailingSlash = false; // For development
}

module.exports = nextConfig;