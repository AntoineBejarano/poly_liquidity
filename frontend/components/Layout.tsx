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
    return null; // Will redirect
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/30">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto">{children}</div>
      </main>
    </div>
  );
}

