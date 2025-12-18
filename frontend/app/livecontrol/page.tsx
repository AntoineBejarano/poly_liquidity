'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@stackframe/stack';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export default function LiveControlPage() {
  const user = useUser();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      // Redirigir al nuevo dashboard
      router.replace('/dashboard');
    }
  }, [user, router]);

  return <LoadingSpinner fullScreen text="Redirigiendo al Dashboard..." />;
}
