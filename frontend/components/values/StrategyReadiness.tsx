'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Zap, ExternalLink, CheckCircle2, Pause, XCircle, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface ValueSignal {
  id: string;
  event: string;
  market: string;
  type: 'surebet' | 'near-resolution' | 'liquidity-gap' | 'custom';
}

interface StrategyInfo {
  id: string;
  name: string;
  status: 'ready' | 'paused' | 'capital-exhausted' | 'missing-config';
  compatibleWith: string[];
}

interface StrategyReadinessProps {
  values: ValueSignal[];
}

export function StrategyReadiness({ values }: StrategyReadinessProps) {
  const router = useRouter();

  // Mock strategies - in real app, fetch from API
  const strategies: StrategyInfo[] = [
    {
      id: 'strategy-1',
      name: 'Surebet High Confidence',
      status: 'ready',
      compatibleWith: ['surebet'],
    },
    {
      id: 'strategy-2',
      name: 'Liquidity Near Resolution',
      status: 'paused',
      compatibleWith: ['near-resolution'],
    },
  ];

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { className: string; icon: React.ReactNode; label: string }> = {
      ready: {
        className: 'bg-green-50 text-green-700 border-green-200',
        icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
        label: 'Ready',
      },
      paused: {
        className: 'bg-yellow-50 text-yellow-700 border-yellow-200',
        icon: <Pause className="h-3 w-3 mr-1" />,
        label: 'Paused',
      },
      'capital-exhausted': {
        className: 'bg-orange-50 text-orange-700 border-orange-200',
        icon: <AlertCircle className="h-3 w-3 mr-1" />,
        label: 'Capital Exhausted',
      },
      'missing-config': {
        className: 'bg-red-50 text-red-700 border-red-200',
        icon: <XCircle className="h-3 w-3 mr-1" />,
        label: 'Missing Config',
      },
    };
    const config = variants[status] || variants.ready;
    return (
      <Badge variant="outline" className={config.className}>
        {config.icon}
        {config.label}
      </Badge>
    );
  };

  const getCompatibleValues = (strategy: StrategyInfo) => {
    return values.filter(v => strategy.compatibleWith.includes(v.type));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Execution Readiness
        </CardTitle>
      </CardHeader>
      <CardContent>
        {strategies.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground text-sm">
            No hay estrategias configuradas
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Estrategia</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Values Compatibles</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategies.map((strategy) => {
                const compatibleValues = getCompatibleValues(strategy);
                return (
                  <TableRow key={strategy.id}>
                    <TableCell className="font-medium">{strategy.name}</TableCell>
                    <TableCell>
                      {getStatusBadge(strategy.status)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">
                          {compatibleValues.length} values
                        </Badge>
                        {compatibleValues.length > 0 && (
                          <span className="text-xs text-muted-foreground">
                            ({compatibleValues.map(v => v.event).slice(0, 2).join(', ')}...)
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => router.push(`/strategies/${strategy.id}`)}
                        >
                          Ver Estrategia
                        </Button>
                        {strategy.status === 'ready' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => router.push(`/strategies/${strategy.id}/live`)}
                          >
                            <ExternalLink className="h-3 w-3 mr-1" />
                            Live Control
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

