'use client';

import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';
import { DynamicBreadcrumbs } from './DynamicBreadcrumbs';
import { ThemeToggle } from './ThemeToggle';
import { DataModeToggle } from './DataModeToggle';
import { useUser } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { useEffect, Suspense } from 'react';
import { LoadingSpinner } from './LoadingSpinner';
import { useDataMode } from '@/hooks/useDataMode';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Database } from 'lucide-react';

function LayoutContent({ children }: { children: React.ReactNode }) {
  const user = useUser();
  const router = useRouter();
  const { isSimulation } = useDataMode();

  useEffect(() => {
    if (!user && typeof window !== 'undefined') {
      router.push('/');
    }
  }, [user, router]);

  if (!user) {
    return null;
  }

  return (
    <>
      <CommandPalette />
      <div className="flex h-screen bg-background overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header compacto: modo de datos + tema */}
          <header className="h-10 border-b border-border bg-card flex items-center justify-end gap-1 px-3 flex-shrink-0">
            <DataModeToggle />
            <ThemeToggle />
          </header>
          {/* Banner global Modo Simulación: datos reales, ejecución DRY_RUN */}
          {isSimulation && (
            <Alert className="rounded-none border-x-0 border-t-0 border-b border-border bg-blue-50 dark:bg-blue-950/30 text-blue-900 dark:text-blue-100 py-1.5 px-3 flex flex-row items-center gap-2 [&>svg]:static [&>svg]:left-auto [&>svg]:top-auto [&>svg~*]:pl-0">
              <Database className="h-4 w-4 flex-shrink-0 text-blue-600 dark:text-blue-400" />
              <AlertDescription className="text-xs p-0">
                <strong>Modo Simulación</strong>
                {' — '}
                Datos del backend; las órdenes se simulan (DRY_RUN). Cambia a Real en el selector para enviar órdenes reales.
              </AlertDescription>
            </Alert>
          )}
          <main className="flex-1 overflow-y-auto">
            <div className="min-h-full px-3 py-2 max-w-[1920px] mx-auto w-full">
              <DynamicBreadcrumbs />
              {children}
            </div>
          </main>
        </div>
      </div>
    </>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Cargando..." />}>
      <LayoutContent>{children}</LayoutContent>
    </Suspense>
  );
}
