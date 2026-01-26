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
import { AlertCircle, RefreshCw, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExecutionAttempt {
  id: string;
  timestamp: string;
  eventName: string;
  action: 'pm_buy' | 'pn_hedge' | 'pm_sell' | 'pn_buy';
  status: 'pending' | 'filled' | 'partial' | 'failed';
  executionTime?: number; // ms
  flags?: string[]; // 'partial_fill', 'venue_mismatch', 'retry_triggered'
}

interface ExecutionPipelineProps {
  executions: ExecutionAttempt[];
}

export function ExecutionPipeline({ executions }: ExecutionPipelineProps) {
  const getStatusBadge = (status: ExecutionAttempt['status']) => {
    switch (status) {
      case 'pending':
        return (
          <Badge variant="warning" className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Pending
          </Badge>
        );
      case 'filled':
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Filled
          </Badge>
        );
      case 'partial':
        return (
          <Badge variant="warning" className="flex items-center gap-1">
            <AlertCircle className="h-3 w-3" />
            Partial
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        );
    }
  };

  const getActionLabel = (action: ExecutionAttempt['action']) => {
    switch (action) {
      case 'pm_buy':
        return 'PM Buy';
      case 'pm_sell':
        return 'PM Sell';
      case 'pn_hedge':
        return 'PN Hedge';
      case 'pn_buy':
        return 'PN Buy';
    }
  };

  if (executions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Execution Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay ejecuciones en el pipeline.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Execution Pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Evento</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Tiempo (ms)</TableHead>
                <TableHead>Flags</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions.map((exec) => (
                <TableRow key={exec.id}>
                  <TableCell className="text-xs text-muted-foreground">
                    {exec.timestamp}
                  </TableCell>
                  <TableCell className="font-medium text-sm">{exec.eventName}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{getActionLabel(exec.action)}</Badge>
                  </TableCell>
                  <TableCell>{getStatusBadge(exec.status)}</TableCell>
                  <TableCell>
                    {exec.executionTime !== undefined ? (
                      <span className={cn(
                        "text-sm",
                        exec.executionTime < 500 ? "text-green-600" :
                        exec.executionTime < 1000 ? "text-yellow-600" : "text-red-600"
                      )}>
                        {exec.executionTime}ms
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {exec.flags && exec.flags.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {exec.flags.map((flag, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">
                            {flag === 'partial_fill' && 'Partial Fill'}
                            {flag === 'venue_mismatch' && 'Venue Mismatch'}
                            {flag === 'retry_triggered' && (
                              <span className="flex items-center gap-1">
                                <RefreshCw className="h-2 w-2" />
                                Retry
                              </span>
                            )}
                          </Badge>
                        ))}
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

