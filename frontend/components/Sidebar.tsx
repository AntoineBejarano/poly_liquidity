'use client';

import { useState, useEffect, type MouseEvent } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Strategy } from '@/types/strategy';
import { cn } from '@/lib/utils';
import { AppVersion } from './AppVersion';
import { useStrategiesOptional } from '@/contexts/StrategiesContext';

export function Sidebar({
  className,
  onNavigate,
  isConnected = false,
}: {
  className?: string;
  onNavigate?: () => void;
  isConnected?: boolean;
}) {
  const pathname = usePathname();
  const user = useUser();
  const stackApp = useStackApp();
  const strategiesContext = useStrategiesOptional();
  const strategies = strategiesContext?.strategies ?? [];
  const strategiesLoading = strategiesContext?.loading ?? false;
  const [isDashboardsExpanded, setIsDashboardsExpanded] = useState(false);
  const [isLiveControlExpanded, setIsLiveControlExpanded] = useState(true);
  const [isMyStrategiesExpanded, setIsMyStrategiesExpanded] = useState(true);

  // Auto-expand sections based on current path
  useEffect(() => {
    if (pathname?.includes('/live')) {
      setIsLiveControlExpanded(true);
    }
    if (pathname?.includes('/dashboard')) {
      setIsDashboardsExpanded(true);
    }
    if (pathname?.startsWith('/strategies/') && !pathname?.includes('/live')) {
      setIsMyStrategiesExpanded(true);
    }
  }, [pathname]);

  const handleNavigate = () => {
    onNavigate?.();
  };

  const handleStopPropagation = (event: MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    onNavigate?.();
  };

  const getStrategyStatus = (strategy: Strategy): { status: 'running' | 'degraded' | 'paused' | 'error'; label: string } => {
    // TODO: Get actual status from backend
    if (!strategy.is_active) {
      return { status: 'paused', label: 'Paused' };
    }
    // Mock logic - replace with actual status from backend
    return { status: 'running', label: 'Running' };
  };

  const getStatusIcon = (status: 'running' | 'degraded' | 'paused' | 'error') => {
    switch (status) {
      case 'running':
        return <span className="w-2 h-2 rounded-full bg-primary flex-shrink-0" title="Running" />;
      case 'degraded':
        return <span className="w-2 h-2 rounded-full bg-[hsl(var(--warning))] flex-shrink-0" title="Degraded" />;
      case 'paused':
        return <span className="w-2 h-2 rounded-full bg-muted-foreground/80 flex-shrink-0" title="Paused" />;
      case 'error':
        return <span className="w-2 h-2 rounded-full bg-destructive flex-shrink-0" title="Error" />;
    }
  };

  const activeStrategies = strategies.filter(s => s.is_active);

  const navItemBase = "flex items-center gap-2 pl-2 pr-2.5 py-1.5 rounded-[var(--radius)] text-[13px] transition-colors cursor-pointer relative";
  const navItemDefault = "text-muted-foreground hover:bg-accent/50 hover:text-foreground";
  const navItemActive = "bg-primary/15 text-primary font-medium";

  const renderNavItem = (href: string, label: string, isActive: boolean) => {
    return (
      <Link
        href={href}
        className={`${navItemBase} ${isActive ? navItemActive : navItemDefault}`}
        onClick={handleNavigate}
      >
        {isActive && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-primary/80" aria-hidden />
        )}
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 shrink-0" />
        <span className="truncate">{label}</span>
      </Link>
    );
  };

  const renderNavSection = (title: string, items: Array<{ name: string; href: string }>) => {
    return (
      <div className="mb-4">
        <div className="px-2 py-1.5 mb-1">
          <span className="text-[0.65rem] font-semibold text-muted-foreground tracking-widest uppercase">{title}</span>
        </div>
        <div className="space-y-0.5">
          {items.map((item) => {
            const isActive = pathname === item.href;
            return (
              <div key={item.href}>
                {renderNavItem(item.href, item.name, isActive)}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderDashboards = () => {
    const isOnDashboard = pathname?.includes('/dashboard');

    return (
      <div className="mb-4">
        <div className="px-2 py-1.5 mb-1">
          <span className="text-[0.65rem] font-semibold text-muted-foreground tracking-widest uppercase">Dashboards</span>
        </div>
        <div className="space-y-0.5">
          <button
            onClick={() => setIsDashboardsExpanded(!isDashboardsExpanded)}
            className={`w-full flex items-center justify-between pl-2 pr-2.5 py-1.5 rounded-[var(--radius)] text-[13px] transition-colors cursor-pointer relative ${
              isOnDashboard ? navItemActive : navItemDefault
            }`}
          >
            {isOnDashboard && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-primary/80" aria-hidden />
            )}
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 shrink-0" />
              <span className="truncate">Dashboards</span>
            </div>
            <span className="text-[10px] opacity-50 shrink-0 ml-1">{isDashboardsExpanded ? '▼' : '▶'}</span>
          </button>

          {isDashboardsExpanded && (
            <div className="ml-3 mt-0.5 space-y-0.5">
              {[
                { href: '/dashboard/capital', label: 'Capital' },
                { href: '/dashboard/operations', label: 'Operations' },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`${navItemBase} pl-3 ${
                    pathname === href ? navItemActive : navItemDefault
                  }`}
                  onClick={handleStopPropagation}
                >
                  {pathname === href && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3 rounded-full bg-primary/80" aria-hidden />
                  )}
                  <span className="w-1 h-1 rounded-full bg-current opacity-40 shrink-0" />
                  <span className="truncate">{label}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderLiveControl = () => {
    const isOnLiveControl = pathname?.includes('/live');

    return (
      <div className="mb-4">
        <div className="space-y-0.5">
          <div>
            <button
              onClick={() => setIsLiveControlExpanded(!isLiveControlExpanded)}
              className={`w-full flex items-center justify-between pl-2 pr-2.5 py-1.5 rounded-[var(--radius)] text-[13px] transition-colors cursor-pointer relative ${
                isOnLiveControl ? navItemActive : navItemDefault
              }`}
            >
              {isOnLiveControl && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-primary/80" aria-hidden />
              )}
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 shrink-0" />
                <span className="truncate">Live Control</span>
              </div>
              <span className="text-[10px] opacity-50 shrink-0 ml-1">{isLiveControlExpanded ? '▼' : '▶'}</span>
            </button>

            {isLiveControlExpanded && (
              <div className="ml-3 mt-0.5 space-y-0.5">
                {strategiesLoading ? (
                  <div className="px-2 py-1.5 text-[13px] text-muted-foreground">Cargando...</div>
                ) : activeStrategies.length === 0 ? (
                  <div className="px-2 py-1.5 space-y-1">
                    <div className="text-[13px] text-muted-foreground italic">No active strategies</div>
                    <Link
                      href="/strategies/new"
                      className="text-[13px] text-primary hover:underline font-medium block"
                      onClick={handleStopPropagation}
                    >
                      Create strategy
                    </Link>
                  </div>
                ) : (
                  activeStrategies.map((strategy) => {
                    const strategyStatus = getStrategyStatus(strategy);
                    const isActive = pathname === `/strategies/${strategy.id}/live`;

                    return (
                      <Link
                        key={strategy.id}
                        href={`/strategies/${strategy.id}/live`}
                        className={`${navItemBase} pl-3 ${
                          isActive ? navItemActive : navItemDefault
                        }`}
                        onClick={handleStopPropagation}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3 rounded-full bg-primary/80" aria-hidden />
                        )}
                        {getStatusIcon(strategyStatus.status)}
                        <span className="truncate flex-1 min-w-0">{strategy.name}</span>
                      </Link>
                    );
                  })
                )}
              </div>
            )}
          </div>

          {renderNavItem('/values/live', 'Values Live', pathname === '/values/live')}
        </div>
      </div>
    );
  };

  const renderStrategiesSection = () => {
    const isOnStrategiesList = pathname === '/strategies';
    const isOnStrategyConfig = pathname?.startsWith('/strategies/') && !pathname?.includes('/live') && pathname !== '/strategies/new';
    const isStrategiesActive = isOnStrategiesList || isOnStrategyConfig;

    return (
      <div className="mb-4">
        <div className="px-2 py-1.5 mb-1">
          <span className="text-[0.65rem] font-semibold text-muted-foreground tracking-widest uppercase">Strategies</span>
        </div>
        <div className="space-y-0.5">
          <div>
            <div
              className={`w-full flex items-center justify-between pl-2 pr-2.5 py-1.5 rounded-[var(--radius)] text-[13px] transition-colors relative ${
                isStrategiesActive ? navItemActive : navItemDefault
              }`}
            >
              {isStrategiesActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-primary/80" aria-hidden />
              )}
              <Link
                href="/strategies"
                className="flex items-center gap-2 flex-1 min-w-0"
                onClick={handleNavigate}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 shrink-0" />
                <span className="truncate">My Strategies</span>
              </Link>
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); setIsMyStrategiesExpanded(!isMyStrategiesExpanded); }}
                className="p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10 text-[10px] opacity-50 shrink-0 transition-colors cursor-pointer"
                aria-label={isMyStrategiesExpanded ? 'Colapsar' : 'Expandir'}
              >
                {isMyStrategiesExpanded ? '▼' : '▶'}
              </button>
            </div>
            {isMyStrategiesExpanded && (
              <div className="ml-3 mt-0.5 space-y-0.5">
                {strategiesLoading ? (
                  <div className="px-2 py-1.5 text-[13px] text-muted-foreground">Cargando...</div>
                ) : strategies.length === 0 ? (
                  <div className="px-2 py-1.5 space-y-1">
                    <div className="text-[13px] text-muted-foreground italic">No hay estrategias</div>
                    <Link
                      href="/strategies/new"
                      className="text-[13px] text-primary hover:underline font-medium block"
                      onClick={handleStopPropagation}
                    >
                      Crear estrategia
                    </Link>
                  </div>
                ) : (
                  strategies.map((strategy) => {
                    const isActive = pathname === `/strategies/${strategy.id}`;
                    return (
                      <Link
                        key={strategy.id}
                        href={`/strategies/${strategy.id}`}
                        className={`${navItemBase} pl-3 ${isActive ? navItemActive : navItemDefault}`}
                        onClick={handleStopPropagation}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3 rounded-full bg-primary/80" aria-hidden />
                        )}
                        {getStatusIcon(getStrategyStatus(strategy).status)}
                        <span className="truncate flex-1 min-w-0">{strategy.name}</span>
                      </Link>
                    );
                  })
                )}
              </div>
            )}
          </div>
          <Link
            href="/strategies/new"
            className={`${navItemBase} ${pathname === '/strategies/new' ? navItemActive : 'text-primary hover:bg-primary/5'} flex items-center gap-2`}
            onClick={handleNavigate}
          >
            {pathname === '/strategies/new' && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-primary/80" aria-hidden />
            )}
            <span className="text-[13px] leading-none font-medium">+</span>
            <span>New Strategy</span>
          </Link>
        </div>
      </div>
    );
  };

  return (
    <aside className={cn("w-56 bg-card h-screen flex flex-col border-r border-[hsl(var(--border))]/50 flex-shrink-0 surface-panel", className)}>
      <div className="px-3 py-3 border-b border-[hsl(var(--border))]/50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-primary/90 flex items-center justify-center shrink-0">
            <span className="text-xs font-semibold text-primary-foreground">A</span>
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-sm font-semibold text-foreground tracking-tight truncate">AlphaEdge</h1>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-2 py-3 overflow-y-auto overflow-x-hidden min-h-0">
        <div className="space-y-0.5">
          {renderDashboards()}
          {renderLiveControl()}
          {renderStrategiesSection()}
          {renderNavSection('Markets', [
            { name: 'Discovery', href: '/markets' },
            { name: 'Legacy', href: '/markets/legacy' },
          ])}
          {renderNavSection('Analysis', [{ name: 'Decision Traces', href: '/decision-traces' }])}
          {renderNavSection('Settings', [
            { name: 'System', href: '/settings/config' },
            { name: 'Risk', href: '/risk' },
            { name: 'Wallets', href: '/settings/wallets' },
            { name: 'Cuentas', href: '/settings/accounts' },
            { name: 'Proxies', href: '/settings/proxies' },
            { name: 'Checkers', href: '/settings/checkers' },
          ])}
        </div>
      </nav>

      <div className="px-3 py-3 border-t border-[hsl(var(--border))]/50 space-y-2 flex-shrink-0">
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-2 rounded-[var(--radius)] bg-muted/60 border border-[hsl(var(--border))]/40">
          <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
            isConnected ? 'bg-primary' : 'bg-muted-foreground'
          }`} />
          <span className="text-[11px] text-muted-foreground truncate">
            {isConnected ? 'Conectado' : 'Desconectado'}
          </span>
          <span className="text-[10px] text-muted-foreground/70">·</span>
          <AppVersion className="text-[10px] text-muted-foreground/80" />
        </div>

        {user && (
          <div className="px-2 min-w-0">
            <p className="text-[11px] font-medium text-muted-foreground truncate">{user.primaryEmail}</p>
          </div>
        )}
        <button
          onClick={() => {
            onNavigate?.();
            stackApp.signOut();
          }}
          className="w-full px-3 py-2 rounded-[var(--radius)] text-[13px] font-medium border border-[hsl(var(--input))] text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-colors cursor-pointer"
        >
          Cerrar Sesión
        </button>
      </div>
    </aside>
  );
}
