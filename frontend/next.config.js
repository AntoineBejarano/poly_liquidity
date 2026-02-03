/** @type {import('next').NextConfig} */
const nextConfig = {
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

