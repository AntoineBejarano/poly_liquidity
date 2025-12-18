'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Strategy } from '@/types/strategy';
import { Button } from '@/components/ui/button';
import { ExternalLink } from 'lucide-react';
import Link from 'next/link';

interface StrategyInfoProps {
  strategy: Strategy;
}

export function StrategyInfo({ strategy }: StrategyInfoProps) {
  // TODO: Obtener eventos asignados desde el backend
  const assignedEvents = [
    { id: '1', name: 'Event A', status: 'ACTIVE', positions: 2, exposure: 1200 },
    { id: '2', name: 'Event B', status: 'ACTIVE', positions: 1, exposure: 800 },
    { id: '3', name: 'Event C', status: 'UPCOMING', positions: 0, exposure: 0 },
  ];

  const maxExposure = strategy.risk_config?.max_exposure || 5000;
  const maxOrderSize = strategy.risk_config?.max_order_size || 1000;
  const maxDrawdown = strategy.risk_config?.max_drawdown || -10;
  const controlLoopInterval = strategy.control_loop_config?.interval || 10;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
      {/* Configuración */}
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0">
          <CardTitle className="text-base font-semibold">Configuración</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="text-sm font-medium mb-1">Tipo</div>
            <div className="text-sm text-muted-foreground">
              {strategy.tags?.[0] || 'Custom Strategy'}
            </div>
          </div>
          
          <div>
            <div className="text-sm font-medium mb-1">Eventos Asignados</div>
            <div className="text-sm text-muted-foreground">
              {assignedEvents.length} eventos
            </div>
            <div className="mt-2 space-y-1">
              {assignedEvents.map((event) => (
                <div key={event.id} className="flex items-center justify-between text-xs">
                  <span>{event.name}</span>
                  <Badge variant={event.status === 'ACTIVE' ? 'success' : 'default'}>
                    {event.status}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
          
          <div>
            <div className="text-sm font-medium mb-1">Risk Config</div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div>Max Exposure: ${maxExposure.toLocaleString()}</div>
              <div>Max Order Size: ${maxOrderSize.toLocaleString()}</div>
              <div>Max Drawdown: {maxDrawdown}%</div>
            </div>
          </div>
          
          <div>
            <div className="text-sm font-medium mb-1">Control Loop</div>
            <div className="text-xs text-muted-foreground">
              Interval: {controlLoopInterval}s
            </div>
          </div>
          
          <Button variant="outline" size="sm" className="w-full">
            Editar Configuración
          </Button>
        </CardContent>
      </Card>

      {/* Mercados Activos */}
      <Card className="h-full flex flex-col">
        <CardHeader className="flex-shrink-0">
          <CardTitle className="text-base font-semibold">Mercados Activos</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-y-auto space-y-3">
          {assignedEvents.map((event) => (
            <div key={event.id} className="border rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">{event.name}</span>
                <Badge variant={event.status === 'ACTIVE' ? 'success' : 'default'}>
                  {event.status}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground space-y-1">
                <div>Posiciones: {event.positions}</div>
                <div>Exposición: ${event.exposure.toLocaleString()}</div>
                <div>
                  Última operación: {event.positions > 0 ? '5m ago' : 'Esperando inicio'}
                </div>
              </div>
              <Button variant="ghost" size="sm" className="w-full mt-2" asChild>
                <Link href={`/markets/${event.id}`}>
                  <ExternalLink className="h-3 w-3 mr-1" />
                  Ver detalles
                </Link>
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

