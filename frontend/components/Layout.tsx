'use client';

import { Sidebar } from './Sidebar';
import { useUser } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export function Layout({ children }: { children: React.ReactNode }) {
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
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="min-h-full p-6 max-w-[1920px] mx-auto w-full">
          {children}
        </div>
      </main>
    </div>
  );
}
