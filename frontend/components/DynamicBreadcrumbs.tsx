'use client';

import { usePathname } from 'next/navigation';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Home } from 'lucide-react';

const routeNames: Record<string, string> = {
  dashboard: 'Dashboard',
  capital: 'Capital',
  operations: 'Operations',
  strategies: 'Strategies',
  live: 'Live Control',
  builder: 'Builder',
  'decision-traces': 'Decision Traces',
  markets: 'Markets',
  settings: 'Settings',
  config: 'System',
  wallets: 'Wallets',
  checkers: 'Checkers',
  risk: 'Risk Management',
  new: 'New',
  sports: 'Sports',
  legacy: 'Legacy',
  games: 'Games',
  crypto: 'Crypto',
  politics: 'Politics',
};

function getSegmentName(segment: string, segments: string[], index: number): string {
  if (segment === 'live' && segments[0] === 'sports') return 'Live';
  if (segments[0] === 'sports' && index === 1 && segment !== 'live') {
    return segment.toUpperCase();
  }
  return routeNames[segment] || segment;
}

export function DynamicBreadcrumbs() {
  const pathname = usePathname();

  if (!pathname || pathname === '/') return null;

  const segments = pathname.split('/').filter(Boolean);

  // Don't show breadcrumbs for top-level routes
  if (segments.length <= 1) return null;

  const isMarketsOrSports = segments[0] === 'markets' || segments[0] === 'sports';
  let segmentsToShow = segments[0] === 'markets' ? segments.slice(1) : segments;
  if (segments[0] === 'sports' && segments[2] === 'games') {
    segmentsToShow = segments.slice(0, 2);
  }

  return (
    <Breadcrumb className="mb-3 sm:mb-4">
      <BreadcrumbList className="flex-nowrap overflow-x-auto whitespace-nowrap text-xs sm:text-sm">
        <BreadcrumbItem>
          {isMarketsOrSports ? (
            <BreadcrumbLink href="/markets" className="flex items-center gap-1">
              Markets
            </BreadcrumbLink>
          ) : (
            <BreadcrumbLink href="/" className="flex items-center gap-1">
              <Home className="h-3 w-3" />
            </BreadcrumbLink>
          )}
        </BreadcrumbItem>

        {segmentsToShow.map((segment, index) => {
          const isLast = index === segmentsToShow.length - 1;
          let href = segments[0] === 'markets'
            ? '/markets/' + segmentsToShow.slice(0, index + 1).join('/')
            : '/' + segments.slice(0, index + 1).join('/');
          if (segment === 'sports' && !isLast) href = '/markets';
          const name = getSegmentName(segment, segments, index);

          return (
            <div key={`${segment}-${index}`} className="flex items-center gap-2">
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{name}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href={href}>{name}</BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </div>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
