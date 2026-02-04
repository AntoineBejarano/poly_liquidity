'use client';

import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';
import { DynamicBreadcrumbs } from './DynamicBreadcrumbs';
import { ThemeToggle } from './ThemeToggle';
import { DataModeToggle } from './DataModeToggle';
import { useUser } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { useEffect, Suspense, useState } from 'react';
import { LoadingSpinner } from './LoadingSpinner';
import { useDataMode } from '@/hooks/useDataMode';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Database, Menu } from 'lucide-react';

function LayoutContent({ children }: { children: React.ReactNode }) {
  const user = useUser();
  const router = useRouter();
  const { isSimulation } = useDataMode();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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
      <Dialog open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
        <DialogContent className="left-0 top-0 h-full w-[min(85vw,20rem)] max-w-none translate-x-0 translate-y-0 rounded-none sm:rounded-none border-r p-0 gap-0 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]">
          <DialogTitle className="sr-only">Menú principal</DialogTitle>
          <Sidebar className="h-full w-full border-r-0" onNavigate={() => setIsMobileMenuOpen(false)} />
        </DialogContent>
      </Dialog>
      <div className="flex min-h-[100dvh] sm:h-screen bg-background overflow-hidden">
        <Sidebar className="hidden lg:flex" />
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header compacto: modo de datos + tema */}
          <header className="h-12 lg:h-10 border-b border-border bg-card flex items-center justify-between lg:justify-end gap-2 px-3 sm:px-4 flex-shrink-0">
            <div className="flex items-center gap-2 lg:hidden">
              <button
                type="button"
                onClick={() => setIsMobileMenuOpen(true)}
                className="inline-flex items-center justify-center h-9 w-9 rounded-md border border-border bg-background hover:bg-muted transition-colors"
                aria-label="Abrir menú"
              >
                <Menu className="h-4 w-4" />
              </button>
              <span className="text-sm font-semibold text-foreground truncate">AlphaEdge</span>
            </div>
            <div className="flex items-center gap-1">
              <DataModeToggle />
              <ThemeToggle />
            </div>
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
            <div className="min-h-full px-3 sm:px-4 lg:px-6 py-3 sm:py-4 max-w-[1920px] mx-auto w-full">
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
