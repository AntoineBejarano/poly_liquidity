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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TrendingUp, AlertTriangle, XCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ArbitrageOpportunity {
  id: string;
  eventName: string;
  marketName: string;
  polymarketPrice: number;
  pinnacleOdds: number;
  grossEdge: number; // %
  netEdge: number; // % after fees
  status: 'tradable' | 'below_threshold' | 'stale_odds' | 'blocked_by_risk';
  timestamp: string;
}

interface LiveArbitrageSnapshotProps {
  opportunities: ArbitrageOpportunity[];
}

export function LiveArbitrageSnapshot({ opportunities }: LiveArbitrageSnapshotProps) {
  const getStatusBadge = (status: ArbitrageOpportunity['status']) => {
    switch (status) {
      case 'tradable':
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Tradable
          </Badge>
        );
      case 'below_threshold':
        return <Badge variant="warning">Below threshold</Badge>;
      case 'stale_odds':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Stale odds
          </Badge>
        );
      case 'blocked_by_risk':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Blocked by risk
          </Badge>
        );
    }
  };

  if (opportunities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Live Arbitrage Snapshot
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              No hay oportunidades de arbitraje detectadas en este momento.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const tradableCount = opportunities.filter(o => o.status === 'tradable').length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Live Arbitrage Snapshot
          {tradableCount > 0 && (
            <Badge variant="success" className="ml-2">
              {tradableCount} tradable
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Evento / Mercado</TableHead>
                <TableHead>Precio Polymarket</TableHead>
                <TableHead>Odds Pinnacle</TableHead>
                <TableHead>Edge Bruto</TableHead>
                <TableHead>Edge Neto</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {opportunities.map((opp) => (
                <TableRow key={opp.id}>
                  <TableCell>
                    <div className="font-medium">{opp.eventName}</div>
                    <div className="text-xs text-muted-foreground">{opp.marketName}</div>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">{opp.polymarketPrice.toFixed(3)}</span>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">{opp.pinnacleOdds.toFixed(2)}</span>
                  </TableCell>
                  <TableCell>
                    <span className={cn(
                      "font-semibold",
                      opp.grossEdge > 0 ? "text-green-600" : "text-red-600"
                    )}>
                      {opp.grossEdge >= 0 ? '+' : ''}{opp.grossEdge.toFixed(2)}%
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={cn(
                      "font-semibold",
                      opp.netEdge > 0 ? "text-green-600" : "text-red-600"
                    )}>
                      {opp.netEdge >= 0 ? '+' : ''}{opp.netEdge.toFixed(2)}%
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(opp.status)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

