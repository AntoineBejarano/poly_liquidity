import eslintConfigNext from "eslint-config-next";

const nextConfig = Array.isArray(eslintConfigNext) ? eslintConfigNext : [eslintConfigNext];

const config = [
  ...nextConfig,
  {
    ignores: [".next/**", "out/**", "build/**", "node_modules/**"],
  },
];

export default config;
