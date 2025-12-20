'use client';

import { useUser } from '@stackframe/stack';
import { useRouter } from 'next/navigation';
import { useEffect, Suspense } from 'react';
import { LoadingSpinner } from '@/components/LoadingSpinner';

function HomeContent() {
  const user = useUser();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.push('/dashboard/operations');
    } else {
      router.push('/sign-in');
    }
  }, [user, router]);

  return null; // Will redirect
}

export default function Home() {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Cargando..." />}>
      <HomeContent />
    </Suspense>
  );
}


