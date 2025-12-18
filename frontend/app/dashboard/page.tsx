'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@stackframe/stack';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Layout } from '@/components/Layout';

export default function DashboardPage() {
  const router = useRouter();
  const user = useUser();

  useEffect(() => {
    if (user) {
      // Redirect to Operations Dashboard by default
      router.replace('/dashboard/operations');
    }
  }, [user, router]);

  if (!user) {
    return null;
  }

  return (
    <Layout>
      <LoadingSpinner fullScreen text="Redirigiendo..." />
    </Layout>
  );
}
