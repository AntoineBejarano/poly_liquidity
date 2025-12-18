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
import { Button } from '@/components/ui/button';
import { Settings, RefreshCw, XCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EventControl {
  id: string;
  eventName: string;
  status: 'active' | 'frozen' | 'disabled';
  currentEdge: number; // %
  tradesExecuted: number;
  lastExecution?: string;
}

interface EventLevelControlsProps {
  events: EventControl[];
  onDisableEvent?: (id: string) => void;
  onForceSync?: (id: string) => void;
  onManualOverride?: (id: string) => void;
}

export function EventLevelControls({
  events,
  onDisableEvent,
  onForceSync,
  onManualOverride,
}: EventLevelControlsProps) {
  const getStatusBadge = (status: EventControl['status']) => {
    switch (status) {
      case 'active':
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Active
          </Badge>
        );
      case 'frozen':
        return <Badge variant="warning">Frozen</Badge>;
      case 'disabled':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Disabled
          </Badge>
        );
    }
  };

  if (events.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Event-Level Controls</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay eventos activos.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Event-Level Controls</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Evento</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Edge Actual</TableHead>
                <TableHead>Trades</TableHead>
                <TableHead>Última Ejecución</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="font-medium">{event.eventName}</TableCell>
                  <TableCell>{getStatusBadge(event.status)}</TableCell>
                  <TableCell>
                    <span className={cn(
                      "font-semibold",
                      event.currentEdge > 2 ? "text-green-600" :
                      event.currentEdge > 0 ? "text-yellow-600" : "text-red-600"
                    )}>
                      {event.currentEdge >= 0 ? '+' : ''}{event.currentEdge.toFixed(2)}%
                    </span>
                  </TableCell>
                  <TableCell>{event.tradesExecuted}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {event.lastExecution || '-'}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {onForceSync && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onForceSync(event.id)}
                          className="h-7 text-xs"
                          title="Force sync"
                        >
                          <RefreshCw className="h-3 w-3" />
                        </Button>
                      )}
                      {onDisableEvent && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onDisableEvent(event.id)}
                          className="h-7 text-xs"
                          title="Disable event"
                        >
                          <XCircle className="h-3 w-3" />
                        </Button>
                      )}
                      {onManualOverride && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onManualOverride(event.id)}
                          className="h-7 text-xs"
                          title="Manual override"
                        >
                          <Settings className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
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

