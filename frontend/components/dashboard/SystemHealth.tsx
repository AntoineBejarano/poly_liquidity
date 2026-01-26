'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { RefreshCw, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface SystemHealthProps {
  systemActive: boolean;
  activeMarkets: number;
}

interface ConnectionStatus {
  name: string;
  status: 'ok' | 'degraded' | 'error';
  latency?: number;
  lastUpdate?: string;
}

export function SystemHealth({ systemActive, activeMarkets }: SystemHealthProps) {
  // TODO: Obtener datos reales de conexiones desde el backend
  const connections: ConnectionStatus[] = [
    {
      name: 'Polymarket',
      status: 'ok',
      latency: 45,
      lastUpdate: '2s ago',
    },
    {
      name: 'Pinnacle',
      status: 'degraded',
      latency: 250,
      lastUpdate: '15s ago',
    },
  ];

  const recentEvents = [
    { time: '2m ago', message: '[Strategy1] Ejecutó orden', type: 'execution' },
    { time: '5m ago', message: '[Strategy2] Error de conexión', type: 'error' },
    { time: '8m ago', message: '[System] Exposición global al 75%', type: 'warning' },
  ];

  return (
    <div className="space-y-4 h-full flex flex-col">
      {/* Conexiones Externas */}
      <Card className="flex-shrink-0">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Conexiones Externas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {connections.map((conn, index) => (
            <div key={index}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">{conn.name}</span>
                <StatusBadge status={conn.status} />
              </div>
              {conn.latency && (
                <div className="text-xs text-muted-foreground">
                  Latencia: {conn.latency}ms
                </div>
              )}
              {conn.lastUpdate && (
                <div className="text-xs text-muted-foreground">
                  Última actualización: {conn.lastUpdate}
                </div>
              )}
              {conn.status !== 'ok' && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 w-full"
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Reconectar
                </Button>
              )}
              {index < connections.length - 1 && <Separator className="mt-3" />}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Eventos Recientes */}
      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader className="pb-3 flex-shrink-0">
          <CardTitle className="text-base font-semibold">Eventos Recientes</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col min-h-0">
          <div className="space-y-3 flex-1 min-h-0 overflow-y-auto">
            {recentEvents.map((event, index) => (
              <div key={index} className="text-sm">
                <div className="text-xs text-muted-foreground mb-1">
                  {event.time}
                </div>
                <div className={cn(
                  "text-sm",
                  event.type === 'error' && "text-red-600",
                  event.type === 'warning' && "text-yellow-600",
                )}>
                  {event.message}
                </div>
                {index < recentEvents.length - 1 && <Separator className="mt-3" />}
              </div>
            ))}
          </div>
          <div className="flex-shrink-0 pt-4 border-t border-border mt-4">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              asChild
            >
              <Link href="/logs">
                <ExternalLink className="h-3 w-3 mr-1" />
                Ver todos los eventos
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


