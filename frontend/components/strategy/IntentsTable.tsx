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
import { ExecutionIntent } from '@/types/strategy';
import Link from 'next/link';
import { ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

interface IntentsTableProps {
  intents: ExecutionIntent[];
  strategyId: string;
  /** Compact variant: no card, dense rows, hairline separator */
  variant?: 'default' | 'compact';
  /** Datos desactualizados (>15 s) */
  isStale?: boolean;
}

export function IntentsTable({ intents, strategyId, variant = 'default', isStale }: IntentsTableProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'EXECUTED':
        return <Badge variant="success">✅ Exec</Badge>;
      case 'APPROVED':
        return <Badge variant="success">Aprobado</Badge>;
      case 'REJECTED':
        return <Badge variant="error">❌ Reject</Badge>;
      case 'PENDING':
        return <Badge variant="warning">Pendiente</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const tableContent = (
    <Table>
      <TableHeader>
        <TableRow className={cn(variant === 'compact' && 'border-b border-border/40')}>
          <TableHead className={cn(variant === 'compact' && 'text-[11px] py-1.5 px-3')}>Timestamp</TableHead>
          <TableHead className={cn(variant === 'compact' && 'text-[11px] py-1.5 px-3')}>Evento</TableHead>
          <TableHead className={cn(variant === 'compact' && 'text-[11px] py-1.5 px-3')}>Acción</TableHead>
          <TableHead className={cn(variant === 'compact' && 'text-[11px] py-1.5 px-3')}>Estado</TableHead>
          <TableHead className={cn(variant === 'compact' && 'text-[11px] py-1.5 px-3')}>Resultado</TableHead>
          <TableHead className={cn(variant === 'compact' && 'text-[11px] py-1.5 px-3 w-8')} />
        </TableRow>
      </TableHeader>
      <TableBody>
        {intents.map((intent) => (
          <TableRow key={intent.id} className={cn(variant === 'compact' && 'border-b border-border/30 hover:bg-muted/20')}>
            <TableCell className={cn('text-xs text-muted-foreground tabular-nums', variant === 'compact' && 'py-1.5 px-3 text-[12px]')}>
              {intent.created_at ? getTimeAgo(intent.created_at) : 'N/A'}
            </TableCell>
            <TableCell className={cn(variant === 'compact' && 'py-1.5 px-3 text-[12px]')}>
              Event {intent.event_id?.substring(0, 8) || 'N/A'}
            </TableCell>
            <TableCell className={cn(variant === 'compact' && 'py-1.5 px-3')}>
              <div className={cn('font-medium tabular-nums', variant === 'compact' ? 'text-[12px]' : 'text-sm')}>
                {intent.side} ${intent.size_usdc?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
              </div>
              <div className="text-xs text-muted-foreground">
                @ {intent.target_price?.toFixed(2) || '0.00'}
              </div>
            </TableCell>
            <TableCell className={cn(variant === 'compact' && 'py-1.5 px-3')}>
              {getStatusBadge(intent.status)}
            </TableCell>
            <TableCell className={cn(variant === 'compact' && 'py-1.5 px-3 text-[12px]')}>
              {intent.status === 'EXECUTED' && intent.order_id ? (
                <span>Orden #{intent.order_id.substring(0, 8)}</span>
              ) : intent.status === 'REJECTED' ? (
                <span className="text-destructive">{intent.reason || 'Rechazado'}</span>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </TableCell>
            <TableCell className={cn(variant === 'compact' && 'py-1.5 px-3')}>
              {intent.trace_id && (
                <Link href={`/decision-traces/${intent.trace_id}`}>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                </Link>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );

  const stalenessIndicator = isStale && variant === 'compact' && (
    <span
      className="inline-block w-2 h-2 rounded-full bg-amber-500 ml-2"
      title="Datos desactualizados (>15 s)"
    />
  );

  if (intents.length === 0) {
    if (variant === 'compact') {
      return (
        <div className="border-b border-border/40 py-4">
          <h3 className="text-h3 mb-2 flex items-center">
            Feed de Ejecución
            {stalenessIndicator}
          </h3>
          <p className="text-sm text-muted-foreground">No hay ejecuciones aún.</p>
        </div>
      );
    }
    return (
      <Card>
        <CardHeader>
          <CardTitle>Últimas Operaciones / Intents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay ejecuciones aún.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variant === 'compact') {
    return (
      <div className="border-b border-border/40">
        <h3 className="text-h3 py-2 flex items-center">
          Feed de Ejecución
          {stalenessIndicator}
        </h3>
        <div className="overflow-x-auto">
          {tableContent}
        </div>
      </div>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Últimas Operaciones / Intents</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col">
        <div className="flex-1 min-h-0 overflow-auto">
          {tableContent}
        </div>
      </CardContent>
    </Card>
  );
}

