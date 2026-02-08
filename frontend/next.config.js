/** @type {import('next').NextConfig} */
// standalone solo en Docker/CI; en Windows local los symlinks dan EPERM sin admin/Developer Mode
const useStandalone = process.env.NEXT_STANDALONE === '1' || process.env.CI === 'true';
const nextConfig = {
  ...(useStandalone ? { output: 'standalone' } : {}),
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

