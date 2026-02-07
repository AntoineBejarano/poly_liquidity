'use client';

import { useEffect, useState } from 'react';
import { useDataModeContext, type DataMode } from '@/contexts/DataModeContext';
import { useUser, useStackApp } from '@stackframe/stack';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Beaker, Database, Zap } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useConfirmDialog } from '@/contexts/NotificationContext';

const MODES: { value: DataMode; label: string; description: string; icon: typeof Beaker }[] = [
  { value: 'demo', label: 'Demo', description: 'Datos de ejemplo, sin backend', icon: Beaker },
  { value: 'simulation', label: 'Simulación', description: 'Datos reales, ejecución DRY_RUN', icon: Database },
  { value: 'real', label: 'Real', description: 'Datos y órdenes reales (LIVE)', icon: Zap },
];

export function DataModeToggle({ isConnected = false }: { isConnected?: boolean }) {
  const { dataMode, setDataMode } = useDataModeContext();
  const user = useUser();
  const stackApp = useStackApp();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const current = MODES.find((m) => m.value === dataMode) ?? MODES[2];
  const Icon = current.icon;

  const handleSelectMode = async (value: DataMode) => {
    if (value === 'real') {
      const confirmed = await confirmDialog({
        title: 'Modo Real (LIVE)',
        description: '¿Activar modo Real (LIVE)? El backend enviará órdenes reales. ¿Continuar?',
      });
      if (!confirmed) return;
    }

    setDataMode(value);

    if (!user || !stackApp || !isConnected) return;
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      if (value === 'simulation') {
        await api.post('/live/status/execution-mode?mode=DRY_RUN');
      } else if (value === 'real') {
        await api.post('/live/status/execution-mode?mode=LIVE');
      }
      // Demo: no se cambia el backend
    } catch (err) {
      console.error('Error syncing execution mode:', err);
    }
  };

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" aria-label="Modo de datos">
        <Zap className="h-5 w-5" />
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Modo de datos" title={`Datos: ${current.label}`}>
          <Icon className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {MODES.map(({ value, label, description, icon: ModeIcon }) => (
          <DropdownMenuItem
            key={value}
            onClick={() => handleSelectMode(value)}
            className={dataMode === value ? 'bg-accent' : ''}
          >
            <ModeIcon className="mr-2 h-4 w-4 flex-shrink-0" />
            <div className="flex flex-col">
              <span>{label}</span>
              <span className="text-xs text-muted-foreground font-normal">{description}</span>
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
