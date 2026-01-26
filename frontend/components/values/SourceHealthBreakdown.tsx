'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Link2, CheckCircle2, AlertCircle, XCircle } from 'lucide-react';

interface SourceInfo {
  id: string;
  name: string;
  timestamp: string;
  latency: number;
  stability: number;
  status: 'synced' | 'lagging' | 'out-of-sync';
}

interface ValueSignal {
  id: string;
  event: string;
  market: string;
  sources: SourceInfo[];
}

interface SourceHealthBreakdownProps {
  values: ValueSignal[];
  selectedValue: ValueSignal | null;
}

export function SourceHealthBreakdown({ values, selectedValue }: SourceHealthBreakdownProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'synced':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case 'lagging':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      case 'out-of-sync':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { className: string }> = {
      synced: { className: 'bg-green-50 text-green-700 border-green-200' },
      lagging: { className: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
      'out-of-sync': { className: 'bg-red-50 text-red-700 border-red-200' },
    };
    const config = variants[status] || variants.synced;
    return (
      <Badge variant="outline" className={config.className}>
        {status === 'synced' ? 'Synced' : status === 'lagging' ? 'Lagging' : 'Out-of-sync'}
      </Badge>
    );
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const secondsAgo = Math.floor((Date.now() - date.getTime()) / 1000);
    if (secondsAgo < 60) return `${secondsAgo}s ago`;
    const minutesAgo = Math.floor(secondsAgo / 60);
    return `${minutesAgo}m ago`;
  };

  const valuesToShow = selectedValue ? [selectedValue] : values;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Link2 className="h-5 w-5" />
          Signal Sources
          {selectedValue && (
            <Badge variant="outline" className="ml-2">
              Filtrado: {selectedValue.event}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {valuesToShow.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground text-sm">
            No hay sources disponibles
          </div>
        ) : (
          <div className="space-y-4">
            {valuesToShow.map((value) => (
              <div key={value.id} className="space-y-2">
                <div className="text-sm font-medium">
                  {value.event} - {value.market}
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fuente</TableHead>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Latencia</TableHead>
                      <TableHead>Estabilidad</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {value.sources.map((source) => (
                      <TableRow key={source.id}>
                        <TableCell className="font-medium">{source.name}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatTimestamp(source.timestamp)}
                        </TableCell>
                        <TableCell>
                          <span className={source.latency > 500 ? 'text-yellow-600' : 'text-green-600'}>
                            {source.latency}ms
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-muted rounded-full h-2">
                              <div
                                className="bg-primary h-2 rounded-full"
                                style={{ width: `${source.stability * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {(source.stability * 100).toFixed(0)}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(source.status)}
                            {getStatusBadge(source.status)}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

