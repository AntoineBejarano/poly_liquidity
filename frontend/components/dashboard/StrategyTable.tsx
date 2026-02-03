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
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { Button } from '@/components/ui/button';
import { Strategy } from '@/types/strategy';
import Link from 'next/link';
import { Play, Pause, Square, ArrowRight } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface StrategyTableProps {
  strategies: Strategy[];
}

export function StrategyTable({ strategies }: StrategyTableProps) {
  const getStatus = (strategy: Strategy): 'running' | 'paused' | 'stopped' | 'error' | 'degraded' => {
    if (strategy.is_active) {
      return 'running';
    }
    if (strategy.disabled_at) {
      return 'stopped';
    }
    return 'paused';
  };

  const getHealth = (strategy: Strategy): 'ok' | 'degraded' | 'error' => {
    // TODO: Implementar lógica real de health basada en métricas
    if (!strategy.is_active) {
      return 'error';
    }
    return 'ok';
  };

  const getRiskLevel = (strategy: Strategy): number => {
    // TODO: Calcular riesgo real basado en exposición y límites
    return 0;
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Estrategias</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col">
        {strategies.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-sm mb-4">No hay estrategias creadas aún.</p>
            <Link href="/strategies/create">
              <Button variant="outline" size="sm">
                Crear Estrategia
              </Button>
            </Link>
          </div>
        ) : (
          <div className="flex-1 min-h-0 overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Estado</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>PnL</TableHead>
                  <TableHead>Exposición</TableHead>
                  <TableHead>Riesgo</TableHead>
                  <TableHead>Health</TableHead>
                  <TableHead>Última Acción</TableHead>
                  <TableHead>Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {strategies.map((strategy) => {
                  const status = getStatus(strategy);
                  const health = getHealth(strategy);
                  const riskLevel = getRiskLevel(strategy);
                  
                  return (
                    <TableRow key={strategy.id}>
                      <TableCell>
                        <StatusBadge status={status} />
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/strategies/${strategy.id}`}
                          className="font-medium hover:underline min-w-0 truncate block"
                        >
                          {strategy.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <span className="text-muted-foreground">$0.00</span>
                      </TableCell>
                      <TableCell>
                        <span className="text-muted-foreground">$0.00</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 min-w-[80px]">
                          <Progress value={riskLevel} className="h-2 flex-1 min-w-0" />
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {riskLevel}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={health} />
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-muted-foreground">
                          {strategy.updated_at
                            ? new Date(strategy.updated_at).toLocaleDateString('es-ES', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : 'N/A'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {strategy.is_active ? (
                            <>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 flex-shrink-0"
                                title="Pausar"
                              >
                                <Pause className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 flex-shrink-0"
                                title="Detener"
                              >
                                <Square className="h-4 w-4" />
                              </Button>
                            </>
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 flex-shrink-0"
                              title="Iniciar"
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          <Link href={`/strategies/${strategy.id}`}>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 flex-shrink-0"
                              title="Ver detalles"
                            >
                              <ArrowRight className="h-4 w-4" />
                            </Button>
                          </Link>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

