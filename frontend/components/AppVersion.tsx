'use client';

/**
 * Muestra la versión de la app (inyectada en build: NEXT_PUBLIC_APP_VERSION).
 * Para Docker: --build-arg NEXT_PUBLIC_APP_VERSION=$(git describe --tags --always)
 */
const version = process.env.NEXT_PUBLIC_APP_VERSION || 'dev';

export function AppVersion({ className }: { className?: string }) {
  return (
    <span
      className={className}
      title={`Versión: ${version}`}
    >
      v{version}
    </span>
  );
}
