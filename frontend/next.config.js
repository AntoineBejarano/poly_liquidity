/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  ignoreWarnings: [
    { module: /@stackframe\/stack/ },
  ],
}

module.exports = nextConfig

