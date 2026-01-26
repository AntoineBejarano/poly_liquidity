'use client';

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

interface Event {
  event_id: string;
  polymarket_event_id: string;
  market_id: string;
  market_name: string;
  start_time: string | null;
  end_time: string | null;
  state: 'UPCOMING' | 'ACTIVE' | 'FINISHED';
  created_at: string;
  updated_at: string;
}

interface EventListProps {
  events: Event[];
  marketFilter?: string;
  stateFilter?: string;
}

export function EventList({ events, marketFilter, stateFilter }: EventListProps) {
  const filteredEvents = events.filter((event) => {
    if (marketFilter && event.market_id !== marketFilter) {
      return false;
    }
    if (stateFilter && stateFilter !== 'all' && event.state !== stateFilter) {
      return false;
    }
    return true;
  });

  const getStateColor = (state: string) => {
    switch (state) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'UPCOMING':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'FINISHED':
        return 'bg-slate-100 text-slate-600 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  if (filteredEvents.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-sm text-muted-foreground">No hay events disponibles</p>
      </Card>
    );
  }

  return (
    <Card>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">Event ID</TableHead>
              <TableHead className="text-xs">Market</TableHead>
              <TableHead className="text-xs">Inicio</TableHead>
              <TableHead className="text-xs">Fin</TableHead>
              <TableHead className="text-xs">Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEvents.map((event) => (
              <TableRow key={event.event_id} className="hover:bg-muted/50">
                <TableCell>
                  <div className="text-xs font-mono text-foreground">
                    {event.polymarket_event_id.substring(0, 20)}...
                  </div>
                </TableCell>
                <TableCell>
                  <div className="text-xs text-foreground">{event.market_name}</div>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                  {event.start_time
                    ? new Date(event.start_time).toLocaleString('es-ES', {
                        day: '2-digit',
                        month: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : '-'}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                  {event.end_time
                    ? new Date(event.end_time).toLocaleString('es-ES', {
                        day: '2-digit',
                        month: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : '-'}
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className={`text-xs ${getStateColor(event.state)}`}>
                    {event.state}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}

