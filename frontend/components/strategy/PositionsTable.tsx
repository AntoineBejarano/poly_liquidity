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
import Link from 'next/link';
import { ExternalLink } from 'lucide-react';

interface Position {
  id: string;
  eventName: string;
  marketName: string;
  size: number;
  avgPrice: number;
  pnl: number;
  status: 'open' | 'pending_close';
}

interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Posiciones Abiertas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay posiciones abiertas actualmente.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Posiciones Abiertas</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col">
        <div className="flex-1 min-h-0 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Evento</TableHead>
                <TableHead>Mercado</TableHead>
                <TableHead>Tamaño</TableHead>
                <TableHead>Precio Avg</TableHead>
                <TableHead>PnL</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((position) => (
                <TableRow key={position.id}>
                  <TableCell className="font-medium">{position.eventName}</TableCell>
                  <TableCell>{position.marketName}</TableCell>
                  <TableCell>${position.size.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                  <TableCell>{position.avgPrice.toFixed(2)}</TableCell>
                  <TableCell>
                    <span className={position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {position.pnl >= 0 ? '+' : ''}${position.pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={position.status === 'open' ? 'success' : 'warning'}>
                      {position.status === 'open' ? 'Open' : 'Pending Close'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Link href={`/positions/${position.id}`}>
                      <ExternalLink className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                    </Link>
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

