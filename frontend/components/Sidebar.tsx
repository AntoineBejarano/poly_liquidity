'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Strategy } from '@/types/strategy';

const operationNav = [
  { name: 'Posiciones', href: '/positions' },
];

const marketsNav = [
  { name: 'Markets', href: '/markets' },
];

const analysisNav = [
  { name: 'Decision Traces', href: '/decision-traces' },
];

const configNav = [
  { name: 'Sistema', href: '/settings/config' },
  { name: 'Riesgo', href: '/risk' },
  { name: 'Wallets', href: '/settings/wallets' },
  { name: 'Checkers', href: '/settings/checkers' },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategiesExpanded, setStrategiesExpanded] = useState(true);
  const [strategiesLoading, setStrategiesLoading] = useState(false);

  useEffect(() => {
    if (!user) return;

    const loadStrategies = async () => {
      try {
        setStrategiesLoading(true);
        const api = initApiClient(createTokenGetter(user, stackApp));
        const data = await api.get<Strategy[]>('/strategies');
        setStrategies(data);
      } catch (err) {
        console.error('Error loading strategies:', err);
      } finally {
        setStrategiesLoading(false);
      }
    };

    loadStrategies();
  }, [user, stackApp]);

  useEffect(() => {
    if (pathname?.startsWith('/strategies')) {
      setStrategiesExpanded(true);
    }
  }, [pathname]);

  const renderNavSection = (title: string, items: Array<{ name: string; href: string }>) => {
    return (
      <div className="mb-8">
        <div className="px-3 py-2 mb-2">
          <span className="text-[11px] font-semibold text-[#6b7280] tracking-wider">{title}</span>
        </div>
        <div className="space-y-1">
          {items.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
                  isActive
                    ? 'bg-[#f3f4f6] text-[#111827] font-medium'
                    : 'text-[#6b7280] hover:bg-[#f9fafb] hover:text-[#111827]'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60"></span>
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </div>
    );
  };

  const renderLiveControlSection = () => {
    const isLiveControlPath = pathname === '/livecontrol' || pathname?.startsWith('/strategies/') && pathname?.includes('/live');
    
    return (
      <div className="mb-8">
        <button
          onClick={() => setStrategiesExpanded(!strategiesExpanded)}
          className="w-full flex items-center justify-between px-3 py-2 mb-2 hover:bg-[#f9fafb] rounded-lg transition-colors duration-200"
        >
          <span className="text-[11px] font-semibold text-[#6b7280] tracking-wider">Live Control</span>
          <span className="text-xs text-[#9ca3af]">
            {strategiesExpanded ? '▼' : '▶'}
          </span>
        </button>
        
        {strategiesExpanded && (
          <div className="space-y-1">
            <Link
              href="/livecontrol"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
                pathname === '/livecontrol'
                  ? 'bg-[#f3f4f6] text-[#111827] font-medium'
                  : 'text-[#6b7280] hover:bg-[#f9fafb] hover:text-[#111827]'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current opacity-60"></span>
              <span>Principal</span>
            </Link>

            {strategiesLoading ? (
              <div className="px-3 py-2 text-sm text-[#9ca3af]">
                Cargando...
              </div>
            ) : strategies.length === 0 ? (
              <div className="px-3 py-2 text-sm text-[#9ca3af] italic">
                No hay estrategias
              </div>
            ) : (
              strategies.map((strategy) => {
                const isActive = pathname === `/strategies/${strategy.id}/live`;
                return (
                  <Link
                    key={strategy.id}
                    href={`/strategies/${strategy.id}/live`}
                    className={`flex items-center gap-3 px-3 py-2 ml-4 rounded-lg text-sm transition-all duration-200 ${
                      isActive
                        ? 'bg-[#f3f4f6] text-[#111827] font-medium'
                        : 'text-[#6b7280] hover:bg-[#f9fafb] hover:text-[#111827]'
                    }`}
                  >
                    <span className="w-1 h-1 rounded-full bg-current opacity-40"></span>
                    <span className="truncate flex-1">{strategy.name}</span>
                    {strategy.is_active && (
                      <span className="w-2 h-2 rounded-full bg-[#10b981] flex-shrink-0" title="Activa"></span>
                    )}
                  </Link>
                );
              })
            )}
          </div>
        )}
      </div>
    );
  };

  const renderStrategiesSection = () => {
    return (
      <div className="mb-8">
        <div className="px-3 py-2 mb-2">
          <span className="text-[11px] font-semibold text-[#6b7280] tracking-wider">Estrategias</span>
        </div>
        <div className="space-y-1">
          <Link
            href="/strategies/new"
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
              pathname === '/strategies/new'
                ? 'bg-[#eff6ff] text-[#2563eb] font-medium'
                : 'text-[#2563eb] hover:bg-[#f0f9ff]'
            }`}
          >
            <span className="text-base leading-none">+</span>
            <span>Nueva Estrategia</span>
          </Link>
        </div>
      </div>
    );
  };

  return (
    <div className="w-64 bg-white min-h-screen flex flex-col border-r border-[#e5e7eb]">
      <div className="p-6 border-b border-[#e5e7eb]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#111827] flex items-center justify-center">
            <span className="text-sm font-semibold text-white">P</span>
          </div>
          <div>
            <h1 className="text-base font-semibold text-[#111827] tracking-tight">PolyLiquidity</h1>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 p-4 overflow-y-auto">
        {renderNavSection('Operación', operationNav)}
        {renderLiveControlSection()}
        {renderNavSection('Mercados', marketsNav)}
        {renderNavSection('Análisis', analysisNav)}
        {renderStrategiesSection()}
        {renderNavSection('Configuración', configNav)}
      </nav>

      <div className="p-4 border-t border-[#e5e7eb] space-y-3">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#f9fafb] border border-[#e5e7eb]">
          <div className={`w-2 h-2 rounded-full ${
            isConnected 
              ? 'bg-[#10b981]' 
              : 'bg-[#9ca3af]'
          }`}></div>
          <span className="text-xs text-[#6b7280]">
            {isConnected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>

        {user && (
          <div className="px-3 py-2">
            <p className="text-xs font-medium text-[#6b7280] truncate">{user.primaryEmail}</p>
          </div>
        )}
        <button 
          onClick={() => stackApp.signOut()}
          className="w-full px-3 py-2 rounded-lg text-sm font-medium border border-[#e5e7eb] text-[#6b7280] hover:bg-[#f9fafb] hover:text-[#111827] transition-all duration-200"
        >
          Cerrar Sesión
        </button>
      </div>
    </div>
  );
}
