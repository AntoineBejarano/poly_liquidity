'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: '📊' },
  { name: 'Mercados', href: '/markets', icon: '📈' },
  { name: 'Posiciones', href: '/positions', icon: '💼' },
  { name: 'Historial', href: '/history', icon: '📜' },
  { name: 'Riesgo', href: '/risk', icon: '⚠️' },
  { name: 'LiveControl', href: '/livecontrol', icon: '🔴' },
  { name: 'Configuración', href: '/settings', icon: '⚙️' },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  return (
    <div className="w-72 glass-dark min-h-screen flex flex-col border-r border-slate-700/50">
      <div className="p-6 border-b border-slate-700/50">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl gradient-premium flex items-center justify-center shadow-lg">
            <span className="text-xl font-bold text-white">P</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">PolyLiquidity</h1>
            <p className="text-xs text-slate-400">Trading Desk</p>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-600/20 to-purple-600/20 text-white border border-indigo-500/30 shadow-lg'
                  : 'text-slate-300 hover:bg-slate-800/50 hover:text-white'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-700/50 space-y-3">
        {/* Connection Status Indicator */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-800/50">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              isConnected 
                ? 'bg-green-500 shadow-lg shadow-green-500/50 animate-pulse' 
                : 'bg-red-500 shadow-lg shadow-red-500/50'
            }`}></div>
            <span className="text-xs font-medium text-slate-300">
              {isConnected ? 'Backend Conectado' : 'Backend Desconectado'}
            </span>
          </div>
        </div>

        {user && (
          <div className="p-3 rounded-xl bg-slate-800/50">
            <p className="text-sm font-medium text-white truncate">{user.primaryEmail}</p>
            <p className="text-xs text-slate-400 mt-1">Usuario activo</p>
          </div>
        )}
        <button 
          onClick={() => stackApp.signOut()}
          className="w-full px-4 py-2 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 text-slate-300 hover:text-white transition-all duration-200 text-sm font-medium"
        >
          Cerrar Sesión
        </button>
      </div>
    </div>
  );
}

