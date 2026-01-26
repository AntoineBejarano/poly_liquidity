'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { RefreshCw, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface ConnectionStatus {
  name: string;
  status: 'ok' | 'degraded' | 'error';
  latency?: number;
  lastUpdate?: string;
  type: 'execution' | 'data';
}

interface EventItem {
  time: string;
  message: string;
  type: 'execution' | 'support_graph' | 'decision_graph' | 'warning' | 'error';
  traceId?: string;
}

interface StrategySystemHealthProps {
  connections: ConnectionStatus[];
  events: EventItem[];
}

export function StrategySystemHealth({ connections, events }: StrategySystemHealthProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
      {/* Fuentes Externas */}
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0">
          <CardTitle className="text-base font-semibold">Fuentes Externas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {connections.map((conn, index) => (
            <div key={index}>
              <div className="flex items-center justify-between mb-1">
                <div>
                  <div className="text-sm font-medium">{conn.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {conn.type === 'execution' ? 'Ejecución' : 'Datos'}
                  </div>
                </div>
                <StatusBadge status={conn.status} />
              </div>
              {conn.latency && (
                <div className="text-xs text-muted-foreground">
                  Latencia: {conn.latency}ms (p95: {conn.latency * 2}ms)
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

      {/* Timeline de Eventos */}
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0">
          <CardTitle className="text-base font-semibold">Timeline de Eventos</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col min-h-0">
          <div className="space-y-3 flex-1 min-h-0 overflow-y-auto">
            {events.map((event, index) => (
              <div key={index} className="text-sm">
                <div className="text-xs text-muted-foreground mb-1">
                  {event.time}
                </div>
                <div className={cn(
                  "text-sm",
                  event.type === 'error' && "text-red-600",
                  event.type === 'warning' && "text-yellow-600",
                )}>
                  <span className="font-medium">[{event.type}]</span> {event.message}
                </div>
                {event.traceId && (
                  <Link 
                    href={`/decision-traces/${event.traceId}`}
                    className="text-xs text-blue-600 hover:underline mt-1 inline-block"
                  >
                    Ver trace →
                  </Link>
                )}
                {index < events.length - 1 && <Separator className="mt-3" />}
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
              <Link href={`/strategies/${'strategy-id'}/logs`}>
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

