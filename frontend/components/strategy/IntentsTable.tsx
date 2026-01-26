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

interface IntentsTableProps {
  intents: ExecutionIntent[];
  strategyId: string;
}

export function IntentsTable({ intents, strategyId }: IntentsTableProps) {
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

  if (intents.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Últimas Operaciones / Intents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay intents generados aún.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Últimas Operaciones / Intents</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col">
        <div className="flex-1 min-h-0 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Evento</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Resultado</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {intents.map((intent) => (
                <TableRow key={intent.id}>
                  <TableCell className="text-xs text-muted-foreground">
                    {intent.created_at ? getTimeAgo(intent.created_at) : 'N/A'}
                  </TableCell>
                  <TableCell className="text-sm">
                    Event {intent.event_id?.substring(0, 8) || 'N/A'}
                  </TableCell>
                  <TableCell>
                    <div className="text-sm font-medium">
                      {intent.side} ${intent.size_usdc?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      @ {intent.target_price?.toFixed(2) || '0.00'}
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(intent.status)}
                  </TableCell>
                  <TableCell>
                    {intent.status === 'EXECUTED' && intent.order_id ? (
                      <div className="text-xs">
                        Orden #{intent.order_id.substring(0, 8)}
                      </div>
                    ) : intent.status === 'REJECTED' ? (
                      <div className="text-xs text-red-600">
                        {intent.reason || 'Rechazado'}
                      </div>
                    ) : (
                      <div className="text-xs text-muted-foreground">-</div>
                    )}
                  </TableCell>
                  <TableCell>
                    {intent.trace_id && (
                      <Link href={`/decision-traces/${intent.trace_id}`}>
                        <ExternalLink className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                      </Link>
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

