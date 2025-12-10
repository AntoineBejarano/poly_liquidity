'use client';

import { useUser } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { useEffect, Suspense } from 'react';

function HomeContent() {
  const user = useUser();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.push('/dashboard');
    } else {
      router.push('/sign-in');
    }
  }, [user, router]);

  return null; // Will redirect
}

export default function Home() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-premium mb-4 shadow-lg animate-pulse">
            <span className="text-3xl font-bold text-white">P</span>
          </div>
          <p className="text-slate-600 font-medium">Cargando...</p>
        </div>
      </div>
    }>
      <HomeContent />
    </Suspense>
  );
}


