/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // necesario para Docker/Railway (server.js en .next/standalone)
  reactStrictMode: true,
  // Next.js 16: Turbopack por defecto; vacío evita error "webpack config and no turbopack config"
  turbopack: {},
  webpack: (config) => {
    config.ignoreWarnings = [
      { module: /@stackframe\/stack/ },
    ]
    return config
  },
}

module.exports = nextConfig

