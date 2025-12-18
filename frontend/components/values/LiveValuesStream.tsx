'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus, Target, Zap, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ValueSignal {
  id: string;
  type: 'surebet' | 'near-resolution' | 'liquidity-gap' | 'custom';
  event: string;
  market: string;
  venues: string[];
  edgeNet: number;
  edgeDelta: number;
  confidence: 'high' | 'medium' | 'low';
  age: number;
  status: 'fresh' | 'improving' | 'decaying' | 'stale' | 'invalidated';
  lifecycle: 'detected' | 'confirmed' | 'tradable' | 'decaying' | 'invalidated' | 'executing';
}

interface LiveValuesStreamProps {
  values: ValueSignal[];
  onSelectValue: (value: ValueSignal | null) => void;
  selectedValue: ValueSignal | null;
}

export function LiveValuesStream({ values, onSelectValue, selectedValue }: LiveValuesStreamProps) {
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'surebet':
        return <Target className="h-4 w-4" />;
      case 'near-resolution':
        return <Zap className="h-4 w-4" />;
      default:
        return <Target className="h-4 w-4" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'surebet':
        return 'Surebet';
      case 'near-resolution':
        return 'Near-Resolution';
      case 'liquidity-gap':
        return 'Liquidity Gap';
      default:
        return 'Custom';
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; className?: string }> = {
      fresh: { variant: 'default', className: 'bg-green-50 text-green-700 border-green-200' },
      improving: { variant: 'default', className: 'bg-blue-50 text-blue-700 border-blue-200' },
      decaying: { variant: 'secondary', className: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
      stale: { variant: 'outline', className: 'bg-gray-50 text-gray-700 border-gray-200' },
      invalidated: { variant: 'destructive', className: 'bg-red-50 text-red-700 border-red-200' },
    };
    const config = variants[status] || variants.fresh;
    return (
      <Badge variant={config.variant} className={config.className}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const getConfidenceBadge = (confidence: string) => {
    const variants: Record<string, { className: string }> = {
      high: { className: 'bg-green-50 text-green-700 border-green-200' },
      medium: { className: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
      low: { className: 'bg-red-50 text-red-700 border-red-200' },
    };
    const config = variants[confidence] || variants.medium;
    return (
      <Badge variant="outline" className={config.className}>
        {confidence.charAt(0).toUpperCase() + confidence.slice(1)}
      </Badge>
    );
  };

  const getEdgeDeltaIcon = (delta: number) => {
    if (delta > 0.1) return <TrendingUp className="h-3 w-3 text-green-600" />;
    if (delta < -0.1) return <TrendingDown className="h-3 w-3 text-red-600" />;
    return <Minus className="h-3 w-3 text-gray-400" />;
  };

  const formatAge = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="h-5 w-5" />
          Active Values
        </CardTitle>
      </CardHeader>
      <CardContent>
        {values.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No hay values activas en este momento
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tipo</TableHead>
                <TableHead>Evento / Mercado</TableHead>
                <TableHead>Venues</TableHead>
                <TableHead>Edge Neto (%)</TableHead>
                <TableHead>Edge Δ</TableHead>
                <TableHead>Confianza</TableHead>
                <TableHead>Edad</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {values.map((value) => (
                <TableRow
                  key={value.id}
                  className={cn(
                    'cursor-pointer hover:bg-muted/50',
                    selectedValue?.id === value.id && 'bg-muted'
                  )}
                  onClick={() => onSelectValue(selectedValue?.id === value.id ? null : value)}
                >
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getTypeIcon(value.type)}
                      <span className="text-xs">{getTypeLabel(value.type)}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <div className="font-medium text-sm">{value.event}</div>
                      <div className="text-xs text-muted-foreground">{value.market}</div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {value.venues.map((venue, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {venue}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="font-semibold text-green-600">
                      {value.edgeNet.toFixed(2)}%
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {getEdgeDeltaIcon(value.edgeDelta)}
                      <span className={cn(
                        'text-sm',
                        value.edgeDelta > 0.1 && 'text-green-600',
                        value.edgeDelta < -0.1 && 'text-red-600'
                      )}>
                        {value.edgeDelta > 0 ? '+' : ''}{value.edgeDelta.toFixed(2)}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getConfidenceBadge(value.confidence)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatAge(value.age)}
                    </div>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(value.status)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

