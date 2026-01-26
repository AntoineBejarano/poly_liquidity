'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SettingsPage() {
  const router = useRouter();
  
  useEffect(() => {
    // Redirigir a la configuración del sistema por defecto
    router.replace('/settings/config');
  }, [router]);

  return null;
}

