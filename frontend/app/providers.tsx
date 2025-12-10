'use client';

import { StackProvider, StackTheme } from '@stackframe/stack';
import { stackClientApp } from '@/stack/client';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <StackProvider app={stackClientApp}>
      <StackTheme>
        {children}
      </StackTheme>
    </StackProvider>
  );
}

