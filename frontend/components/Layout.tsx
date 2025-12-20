'use client';

import { Sidebar } from './Sidebar';
import { CommandPalette } from './CommandPalette';
import { DynamicBreadcrumbs } from './DynamicBreadcrumbs';
import { ThemeToggle } from './ThemeToggle';
import { useUser } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { useEffect, Suspense } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

function LayoutContent({ children }: { children: React.ReactNode }) {
  const user = useUser();
  const router = useRouter();

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
          {/* Header con Theme Toggle */}
          <header className="h-14 border-b border-border bg-card flex items-center justify-end px-6 flex-shrink-0">
            <ThemeToggle />
          </header>
          <main className="flex-1 overflow-y-auto">
            <div className="min-h-full p-6 max-w-[1920px] mx-auto w-full">
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
