'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Activity } from 'lucide-react';

interface ValueSignal {
  id: string;
  event: string;
  market: string;
  lifecycle: 'detected' | 'confirmed' | 'tradable' | 'decaying' | 'invalidated' | 'executing';
}

interface SignalLifecycleViewProps {
  values: ValueSignal[];
}

export function SignalLifecycleView({ values }: SignalLifecycleViewProps) {
  const getLifecycleBadge = (lifecycle: string) => {
    const variants: Record<string, { className: string; label: string }> = {
      detected: { className: 'bg-blue-50 text-blue-700 border-blue-200', label: 'Detected' },
      confirmed: { className: 'bg-green-50 text-green-700 border-green-200', label: 'Confirmed' },
      tradable: { className: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Tradable' },
      decaying: { className: 'bg-yellow-50 text-yellow-700 border-yellow-200', label: 'Decaying' },
      invalidated: { className: 'bg-red-50 text-red-700 border-red-200', label: 'Invalidated' },
      executing: { className: 'bg-purple-50 text-purple-700 border-purple-200', label: 'Executing' },
    };
    const config = variants[lifecycle] || variants.detected;
    return (
      <Badge variant="outline" className={config.className}>
        {config.label}
      </Badge>
    );
  };

  const lifecycleOrder: Record<string, number> = {
    detected: 1,
    confirmed: 2,
    tradable: 3,
    executing: 4,
    decaying: 5,
    invalidated: 6,
  };

  const sortedValues = [...values].sort((a, b) => 
    (lifecycleOrder[a.lifecycle] || 0) - (lifecycleOrder[b.lifecycle] || 0)
  );

  const lifecycleCounts = values.reduce((acc, value) => {
    acc[value.lifecycle] = (acc[value.lifecycle] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Lifecycle State
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary */}
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-4">
          {Object.entries(lifecycleCounts).map(([lifecycle, count]) => (
            <div key={lifecycle} className="text-center">
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-xs text-muted-foreground capitalize">{lifecycle}</div>
            </div>
          ))}
        </div>

        {/* Detailed table */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Evento / Mercado</TableHead>
              <TableHead>Estado del Ciclo de Vida</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedValues.map((value) => (
              <TableRow key={value.id}>
                <TableCell>
                  <div>
                    <div className="font-medium text-sm">{value.event}</div>
                    <div className="text-xs text-muted-foreground">{value.market}</div>
                  </div>
                </TableCell>
                <TableCell>
                  {getLifecycleBadge(value.lifecycle)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

