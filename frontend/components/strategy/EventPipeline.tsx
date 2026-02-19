'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface EventPipelineItem {
  id: string;
  eventName: string;
  marketName: string;
  currentPrice: number;
  status: 'waiting_for_result' | 'result_confirmed' | 'orders_placed' | 'awaiting_resolution';
  exposure: number;
  estimatedPnL: number;
  timeToResolution?: number; // minutes
}

interface EventPipelineProps {
  events: EventPipelineItem[];
  /** Compact: vertical state list, no card */
  variant?: 'default' | 'compact';
}

export function EventPipeline({ events, variant = 'default' }: EventPipelineProps) {
  const getStatusBadge = (status: EventPipelineItem['status']) => {
    switch (status) {
      case 'waiting_for_result':
        return <Badge variant="warning">Esperando resultado</Badge>;
      case 'result_confirmed':
        return <Badge variant="success">Resultado confirmado</Badge>;
      case 'orders_placed':
        return <Badge variant="default">Órdenes colocadas</Badge>;
      case 'awaiting_resolution':
        return <Badge variant="default">Esperando resolución</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const statusDotClass = (s: EventPipelineItem['status']) => {
    switch (s) {
      case 'result_confirmed': return 'bg-primary';
      case 'orders_placed': return 'bg-primary/70';
      case 'awaiting_resolution': return 'bg-muted-foreground/50';
      case 'waiting_for_result': return 'bg-amber-500';
      default: return 'bg-muted-foreground/30';
    }
  };

  if (events.length === 0) {
    if (variant === 'compact') {
      return (
        <div className="border-b border-border/40 py-4">
          <h3 className="text-h3 mb-2">Pipeline de Eventos</h3>
          <p className="text-sm text-muted-foreground">No hay eventos activos en el pipeline.</p>
        </div>
      );
    }
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Pipeline de Eventos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay eventos activos en el pipeline.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variant === 'compact') {
    return (
      <div className="border-b border-border/40">
        <h3 className="text-h3 py-2">Pipeline de Eventos</h3>
        <div className="space-y-0">
          {events.map((event, i) => (
            <div
              key={event.id}
              className={cn(
                'flex items-center gap-3 py-2 px-0 border-b border-border/30 last:border-b-0',
                'text-[12px]'
              )}
            >
              <div className={cn('w-2 h-2 rounded-full shrink-0', statusDotClass(event.status))} />
              <span className="font-medium min-w-0 truncate">{event.eventName}</span>
              <span className="text-muted-foreground shrink-0">{event.marketName}</span>
              <span className="tabular-nums shrink-0">${event.exposure.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              <span className={cn(
                'tabular-nums shrink-0',
                event.estimatedPnL >= 0 ? 'text-primary' : 'text-destructive'
              )}>
                {event.estimatedPnL >= 0 ? '+' : ''}${event.estimatedPnL.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
              {getStatusBadge(event.status)}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Pipeline de Eventos</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Evento</TableHead>
                <TableHead>Mercado</TableHead>
                <TableHead>Precio Actual</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Exposición</TableHead>
                <TableHead>PnL Estimado</TableHead>
                <TableHead>Tiempo a Resolución</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="font-medium">{event.eventName}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{event.marketName}</TableCell>
                  <TableCell>
                    <span className="font-medium">{event.currentPrice.toFixed(3)}</span>
                  </TableCell>
                  <TableCell>{getStatusBadge(event.status)}</TableCell>
                  <TableCell>
                    <span className="font-medium">${event.exposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </TableCell>
                  <TableCell>
                    <span className={cn(
                      "font-medium",
                      event.estimatedPnL >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      {event.estimatedPnL >= 0 ? '+' : ''}${event.estimatedPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </TableCell>
                  <TableCell>
                    {event.timeToResolution !== undefined ? (
                      <div className="space-y-1">
                        <div className="text-xs text-muted-foreground">
                          {event.timeToResolution} min
                        </div>
                        <Progress 
                          value={Math.max(0, Math.min(100, (event.timeToResolution / 60) * 100))} 
                          className="h-1 w-20"
                        />
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

