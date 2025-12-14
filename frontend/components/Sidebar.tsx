'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';

const operationNav = [
  { name: 'Live Control', href: '/livecontrol' },
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

  const renderNavSection = (title: string, items: Array<{ name: string; href: string }>) => {
    return (
      <div className="mb-6">
        <div className="px-2.5 py-1.5 mb-1">
          <span className="text-xs font-semibold text-slate-900 uppercase tracking-wide">{title}</span>
        </div>
        <div className="space-y-0.5">
          {items.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-2.5 py-1.5 rounded text-xs transition-colors ${
                  isActive
                    ? 'bg-slate-100 text-slate-900 font-medium'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <span className="text-xs">●</span>
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="w-56 bg-white min-h-screen flex flex-col border-r border-slate-200">
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-slate-900 flex items-center justify-center">
            <span className="text-xs font-medium text-white">P</span>
          </div>
          <div>
            <h1 className="text-sm font-medium text-slate-900">PolyLiquidity</h1>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 p-3 overflow-y-auto">
        {renderNavSection('OPERACIÓN', operationNav)}
        {renderNavSection('MERCADOS', marketsNav)}
        {renderNavSection('ANÁLISIS', analysisNav)}
        {renderNavSection('CONFIGURACIÓN', configNav)}
      </nav>

      <div className="p-3 border-t border-slate-200 space-y-2">
        {/* Connection Status Indicator */}
        <div className="flex items-center gap-1.5 px-2 py-1.5 rounded border border-slate-200 bg-slate-50">
          <div className={`w-1.5 h-1.5 rounded-full ${
            isConnected 
              ? 'bg-slate-400' 
              : 'bg-slate-300'
          }`}></div>
          <span className="text-xs text-slate-600">
            {isConnected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>

        {user && (
          <div className="px-2 py-1.5">
            <p className="text-xs font-medium text-slate-900 truncate">{user.primaryEmail}</p>
          </div>
        )}
        <button 
          onClick={() => stackApp.signOut()}
          className="w-full px-2 py-1.5 rounded text-xs font-medium border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Cerrar Sesión
        </button>
      </div>
    </div>
  );
}

