'use client';

import Link from 'next/link';
import { ThemeToggle } from './ThemeToggle';
import { useUser } from '@stackframe/stack';

export function Header() {
  const user = useUser();

  return (
    <header className="w-full border-b border-border bg-card sticky top-0 z-40">
      <div className="container flex items-center justify-between gap-4 py-3">
        <div className="flex items-center gap-3">
          <Link href="/" className="text-title font-semibold hover:text-primary transition-colors">
            AlphaEdge
          </Link>
          {user && (
            <nav className="hidden md:flex gap-2 text-sm text-muted-foreground">
              <Link href="/livecontrol" className="px-2 py-1 rounded hover:bg-accent hover:text-accent-foreground transition-colors">
                Live
              </Link>
              <Link href="/strategies" className="px-2 py-1 rounded hover:bg-accent hover:text-accent-foreground transition-colors">
                Strategies
              </Link>
              <Link href="/positions" className="px-2 py-1 rounded hover:bg-accent hover:text-accent-foreground transition-colors">
                Positions
              </Link>
            </nav>
          )}
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
