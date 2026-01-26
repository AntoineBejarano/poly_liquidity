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
}

export function EventPipeline({ events }: EventPipelineProps) {
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

  if (events.length === 0) {
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

