'use client';

import { StackProvider, StackTheme } from '@stackframe/stack';
import { stackClientApp } from '@/stack/client';
import { ThemeProvider } from 'next-themes';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <StackProvider app={stackClientApp}>
      <StackTheme>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange={false}
        >
          {children}
        </ThemeProvider>
      </StackTheme>
    </StackProvider>
  );
}

