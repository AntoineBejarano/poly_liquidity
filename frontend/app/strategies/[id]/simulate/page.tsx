'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { KPIBar, KPI } from '@/components/ui/kpi-bar';
import { Panel } from '@/components/ui/panel';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { InlineForm } from '@/components/ui/inline-form';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { BarChart3, X } from 'lucide-react';

interface SimulationResult {
  strategy_id: string;
  duration_seconds: number;
  capital_usdc: number;
  fill_mode: string;
  estimated_pnl: number;
  orders_created: number;
  orders_filled: number;
  orders_rejected: number;
  total_volume_usdc: number;
  average_fill_price: number | null;
  win_rate: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  warnings: string[];
  fills_breakdown: Array<{
    event_id: string;
    asset_id: string;
    side: string;
    outcome: string;
    price: number;
    size: number;
    size_usdc: number;
    levels_swept: number;
    timestamp: string;
  }>;
}

export default function SimulationPage() {
  const params = useParams();
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyId = params.id as string;

  const [isOpen, setIsOpen] = useState(true);
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [initialCapital, setInitialCapital] = useState(5000);
  const [fillMode, setFillMode] = useState<'conservative' | 'realistic'>('conservative');
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<SimulationResult | null>(null);

  const handleSimulate = async () => {
    if (!user || !stackApp) return;

    setIsRunning(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      const result = await api.post<SimulationResult>(`/api/strategies/${strategyId}/simulate`, {
        duration_seconds: durationMinutes * 60, // Convertir minutos a segundos
        capital_usdc: initialCapital,
        fill_mode: fillMode,
      });
      setResults(result);
    } catch (err) {
      console.error('Error running simulation:', err);
      alert('Error running simulation. Check console for details.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    router.back();
  };

  return (
    <Layout>
      <Dialog open={isOpen} onOpenChange={handleClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Simulate Strategy</DialogTitle>
          </DialogHeader>

          <div className="space-y-3">
            <InlineForm
              label="Duration"
              tooltip="Tiempo de simulación"
              input={
                <Select value={durationMinutes.toString()} onValueChange={(v) => setDurationMinutes(Number(v))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15 min</SelectItem>
                    <SelectItem value="30">30 min</SelectItem>
                    <SelectItem value="60">60 min</SelectItem>
                  </SelectContent>
                </Select>
              }
            />

            <InlineForm
              label="Initial Capital"
              tooltip="Capital inicial para la simulación"
              input={
                <Input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  placeholder="$"
                />
              }
            />

            <InlineForm
              label="Fill Model"
              tooltip="Conservative = solo mejor nivel. Realistic = barre varios niveles (más realista)"
              input={
                <Select value={fillMode} onValueChange={(v) => setFillMode(v as 'conservative' | 'realistic')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conservative">Conservative</SelectItem>
                    <SelectItem value="realistic">Realistic</SelectItem>
                  </SelectContent>
                </Select>
              }
            />

            <Button
              size="compact"
              onClick={handleSimulate}
              disabled={isRunning}
              className="w-full"
            >
              <BarChart3 className="h-3 w-3 mr-1" />
              {isRunning ? 'Running Simulation...' : 'Run Simulation'}
            </Button>

            {results && (
              <>
                <KPIBar>
                  <KPI
                    label="Est. PnL"
                    value={`$${results.estimated_pnl.toFixed(2)}`}
                    trend={results.estimated_pnl >= 0 ? 'up' : 'down'}
                    tooltip="Profit and Loss estimado"
                  />
                  <KPI
                    label="Fill Rate"
                    value={results.orders_created > 0 
                      ? `${((results.orders_filled / results.orders_created) * 100).toFixed(0)}%`
                      : 'N/A'
                    }
                    tooltip="Porcentaje de órdenes ejecutadas"
                  />
                  <KPI
                    label="Orders"
                    value={`${results.orders_filled}/${results.orders_created}`}
                    tooltip="Órdenes filled / creadas"
                  />
                  <KPI
                    label="Win Rate"
                    value={results.win_rate !== null 
                      ? `${(results.win_rate * 100).toFixed(0)}%`
                      : 'N/A'
                    }
                    tooltip="Porcentaje de trades ganadores"
                  />
                  <KPI
                    label="Volume"
                    value={`$${results.total_volume_usdc.toLocaleString()}`}
                    tooltip="Volumen total ejecutado"
                  />
                </KPIBar>

                {results.warnings.length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-2 text-[12px] text-yellow-800">
                    {results.warnings.map((warning, idx) => (
                      <div key={idx}>⚠️ {warning}</div>
                    ))}
                  </div>
                )}

                <Tabs defaultValue="summary" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="summary">Summary</TabsTrigger>
                    <TabsTrigger value="fills">Fills ({results.fills_breakdown.length})</TabsTrigger>
                  </TabsList>

                  <TabsContent value="summary" className="space-y-2">
                    <Panel>
                      <div className="space-y-2 text-[13px]">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Estimated PnL:</span>
                          <span className={`font-semibold ${results.estimated_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            ${results.estimated_pnl.toFixed(2)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Orders Created:</span>
                          <span>{results.orders_created}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Orders Filled:</span>
                          <span>{results.orders_filled}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Orders Rejected:</span>
                          <span>{results.orders_rejected}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Total Volume:</span>
                          <span>${results.total_volume_usdc.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Avg Fill Price:</span>
                          <span>{results.average_fill_price?.toFixed(4) || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Win Rate:</span>
                          <span>{results.win_rate !== null ? `${(results.win_rate * 100).toFixed(1)}%` : 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Fill Mode:</span>
                          <span className="capitalize">{results.fill_mode}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Capital Used:</span>
                          <span>${results.capital_usdc.toLocaleString()}</span>
                        </div>
                      </div>
                    </Panel>
                  </TabsContent>

                  <TabsContent value="fills">
                    <div className="border rounded-lg overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Asset ID</TableHead>
                            <TableHead>Side</TableHead>
                            <TableHead>Price</TableHead>
                            <TableHead>Size</TableHead>
                            <TableHead>USDC</TableHead>
                            <TableHead>Levels</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {results.fills_breakdown.map((fill, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="font-mono text-[11px]">
                                {fill.asset_id.slice(0, 12)}...
                              </TableCell>
                              <TableCell>
                                <span className={fill.side === 'BUY' ? 'text-green-600' : 'text-red-600'}>
                                  {fill.side} {fill.outcome}
                                </span>
                              </TableCell>
                              <TableCell>{fill.price.toFixed(4)}</TableCell>
                              <TableCell>{fill.size.toFixed(2)}</TableCell>
                              <TableCell>${fill.size_usdc.toFixed(2)}</TableCell>
                              <TableCell>{fill.levels_swept}</TableCell>
                            </TableRow>
                          ))}
                          {results.fills_breakdown.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={6} className="text-center text-muted-foreground">
                                No fills in this simulation
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                </Tabs>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}

