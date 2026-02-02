'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Strategy } from '@/types/strategy';

export function Sidebar() {
  const pathname = usePathname();
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [isDashboardsExpanded, setIsDashboardsExpanded] = useState(false);
  const [isLiveControlExpanded, setIsLiveControlExpanded] = useState(true);
  const [isMyStrategiesExpanded, setIsMyStrategiesExpanded] = useState(true);

  useEffect(() => {
    if (!user || !stackApp) return;

    let cancelled = false;
    let retryId: ReturnType<typeof setTimeout> | null = null;

    const loadStrategies = async () => {
      setStrategiesLoading(true);
      const api = initApiClient(createTokenGetter(user, stackApp));
      try {
        const data = await api.get<Strategy[]>('/api/strategies/summary', true);
        if (!cancelled) setStrategies(Array.isArray(data) ? data : []);
      } catch {
        try {
          const data = await api.get<Strategy[]>('/api/strategies', true);
          if (!cancelled) setStrategies(Array.isArray(data) ? data : []);
        } catch {
          if (!cancelled) setStrategies([]);
          if (!cancelled) retryId = setTimeout(loadStrategies, 2000);
        }
      } finally {
        if (!cancelled) setStrategiesLoading(false);
      }
    };

    loadStrategies();
    return () => {
      cancelled = true;
      if (retryId) clearTimeout(retryId);
    };
  }, [user, stackApp]);

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
        return <span className="w-2 h-2 rounded-full bg-green-500 dark:bg-green-600 flex-shrink-0" title="Running"></span>;
      case 'degraded':
        return <span className="w-2 h-2 rounded-full bg-yellow-500 dark:bg-yellow-600 flex-shrink-0" title="Degraded"></span>;
      case 'paused':
        return <span className="w-2 h-2 rounded-full bg-muted-foreground flex-shrink-0" title="Paused"></span>;
      case 'error':
        return <span className="w-2 h-2 rounded-full bg-red-500 dark:bg-red-600 flex-shrink-0" title="Error"></span>;
    }
  };

  const activeStrategies = strategies.filter(s => s.is_active);

  const renderNavItem = (href: string, label: string, isActive: boolean) => {
    return (
      <Link
        href={href}
        className={`flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-colors ${
          isActive
            ? 'bg-accent text-accent-foreground font-medium'
            : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
        }`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60 shrink-0"></span>
        <span className="truncate">{label}</span>
      </Link>
    );
  };

  const renderNavSection = (title: string, items: Array<{ name: string; href: string }>) => {
    return (
      <div className="mb-3">
        <div className="px-2.5 py-1 mb-0.5">
          <span className="text-[10px] font-semibold text-muted-foreground tracking-wider uppercase">{title}</span>
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
      <div className="mb-3">
        <div className="px-2.5 py-1 mb-0.5">
          <span className="text-[10px] font-semibold text-muted-foreground tracking-wider uppercase">Dashboards</span>
        </div>
        <div className="space-y-0.5">
            <button
              onClick={() => setIsDashboardsExpanded(!isDashboardsExpanded)}
              className={`w-full flex items-center justify-between px-2.5 py-1 rounded-md text-xs transition-colors ${
                isOnDashboard
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60 shrink-0"></span>
                <span className="truncate">Dashboards</span>
              </div>
              <span className="text-[10px] opacity-60 shrink-0 ml-1">
                {isDashboardsExpanded ? '▼' : '▶'}
              </span>
            </button>

          {isDashboardsExpanded && (
            <div className="ml-3 mt-0.5 space-y-0.5">
              <Link
                href="/dashboard/capital"
                className={`flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-colors ${
                  pathname === '/dashboard/capital'
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                }`}
                onClick={(e) => e.stopPropagation()}
              >
                <span className="w-1 h-1 rounded-full bg-current opacity-40 shrink-0"></span>
                <span className="truncate">Capital</span>
              </Link>
              <Link
                href="/dashboard/operations"
                className={`flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-colors ${
                  pathname === '/dashboard/operations'
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                }`}
                onClick={(e) => e.stopPropagation()}
              >
                <span className="w-1 h-1 rounded-full bg-current opacity-40 shrink-0"></span>
                <span className="truncate">Operations</span>
              </Link>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderLiveControl = () => {
    const isOnLiveControl = pathname?.includes('/live');

    return (
      <div className="mb-3">
        <div className="space-y-0.5">
          <div>
            <button
              onClick={() => setIsLiveControlExpanded(!isLiveControlExpanded)}
              className={`w-full flex items-center justify-between px-2.5 py-1 rounded-md text-xs transition-colors ${
                isOnLiveControl
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60 shrink-0"></span>
                <span className="truncate">Live Control</span>
              </div>
              <span className="text-[10px] opacity-60 shrink-0 ml-1">
                {isLiveControlExpanded ? '▼' : '▶'}
              </span>
            </button>

            {isLiveControlExpanded && (
              <div className="ml-3 mt-0.5 space-y-0.5">
                {strategiesLoading ? (
                  <div className="px-2.5 py-1 text-xs text-muted-foreground">Cargando...</div>
                ) : activeStrategies.length === 0 ? (
                  <div className="px-2.5 py-1 space-y-0.5">
                    <div className="text-xs text-muted-foreground italic">No active strategies</div>
                    <Link
                      href="/strategies/new"
                      className="text-xs text-primary hover:underline font-medium block"
                      onClick={(e) => e.stopPropagation()}
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
                        className={`flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-colors ${
                          isActive
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                        }`}
                        onClick={(e) => e.stopPropagation()}
                      >
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

    return (
      <div className="mb-3">
        <div className="px-2.5 py-1 mb-0.5">
          <span className="text-[10px] font-semibold text-muted-foreground tracking-wider uppercase">Strategies</span>
        </div>
        <div className="space-y-0.5">
          <div>
            <div
              className={`w-full flex items-center justify-between px-2.5 py-1 rounded-md text-xs transition-colors ${
                isOnStrategiesList || isOnStrategyConfig
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
              }`}
            >
              <Link
                href="/strategies"
                className="flex items-center gap-2 flex-1 min-w-0"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60 shrink-0"></span>
                <span className="truncate">My Strategies</span>
              </Link>
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); setIsMyStrategiesExpanded(!isMyStrategiesExpanded); }}
                className="p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10 text-[10px] opacity-60 shrink-0"
                aria-label={isMyStrategiesExpanded ? 'Colapsar' : 'Expandir'}
              >
                {isMyStrategiesExpanded ? '▼' : '▶'}
              </button>
            </div>
            {isMyStrategiesExpanded && (
              <div className="ml-3 mt-0.5 space-y-0.5">
                {strategiesLoading ? (
                  <div className="px-2.5 py-1 text-xs text-muted-foreground">Cargando...</div>
                ) : strategies.length === 0 ? (
                  <div className="px-2.5 py-1 space-y-0.5">
                    <div className="text-xs text-muted-foreground italic">No hay estrategias</div>
                    <Link
                      href="/strategies/new"
                      className="text-xs text-primary hover:underline font-medium block"
                      onClick={(e) => e.stopPropagation()}
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
                        className={`flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-colors ${
                          isActive
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                        }`}
                        onClick={(e) => e.stopPropagation()}
                      >
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
            className={`flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-colors ${
              pathname === '/strategies/new'
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-primary hover:bg-primary/5'
            }`}
          >
            <span className="text-xs leading-none font-medium">+</span>
            <span>New Strategy</span>
          </Link>
        </div>
      </div>
    );
  };

  return (
    <aside className="w-56 bg-card h-screen flex flex-col border-r border-border flex-shrink-0">
      <div className="px-2.5 py-2 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center shrink-0">
            <span className="text-xs font-semibold text-primary-foreground">A</span>
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-sm font-semibold text-foreground tracking-tight truncate">AlphaEdge</h1>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-2 py-2 overflow-y-auto overflow-x-hidden min-h-0">
        <div className="space-y-0.5">
          {renderDashboards()}
          {renderLiveControl()}
          {renderStrategiesSection()}
          {renderNavSection('Markets', [{ name: 'Markets', href: '/markets' }])}
          {renderNavSection('Analysis', [{ name: 'Decision Traces', href: '/decision-traces' }])}
          {renderNavSection('Settings', [
            { name: 'System', href: '/settings/config' },
            { name: 'Risk', href: '/risk' },
            { name: 'Wallets', href: '/settings/wallets' },
            { name: 'Checkers', href: '/settings/checkers' },
          ])}
        </div>
      </nav>

      <div className="px-2.5 py-2 border-t border-border space-y-1.5 flex-shrink-0">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-muted/80 border border-border">
          <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
            isConnected
              ? 'bg-green-500 dark:bg-green-600'
              : 'bg-muted-foreground'
          }`}></div>
          <span className="text-[11px] text-muted-foreground truncate">
            {isConnected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>

        {user && (
          <div className="px-2 min-w-0">
            <p className="text-[11px] font-medium text-muted-foreground truncate">{user.primaryEmail}</p>
          </div>
        )}
        <button
          onClick={() => stackApp.signOut()}
          className="w-full px-2.5 py-1 rounded-md text-xs font-medium border border-border text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          Cerrar Sesión
        </button>
      </div>
    </aside>
  );
}
