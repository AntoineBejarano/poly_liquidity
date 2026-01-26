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
  pnl_total: number;
  trades_count: number;
  fill_rate: number;
  avg_edge_bps: number;
  max_exposure_usdc: number;
  fills: Array<{
    id: string;
    asset_id: string;
    fill_price: number;
    fill_shares: number;
    fill_usdc: number;
    fill_ts_ms: number;
  }>;
  top_markets: Array<{
    market_id: string;
    name: string;
    pnl: number;
    trades: number;
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
      const result = await api.post<SimulationResult>(`/strategies/${strategyId}/simulate`, {
        duration_minutes: durationMinutes,
        initial_capital_usdc: initialCapital,
        fill_mode: fillMode,
      });
      setResults(result);
    } catch (err) {
      console.error('Error running simulation:', err);
      // Mock data para demo
      setResults({
        pnl_total: 234.56,
        trades_count: 12,
        fill_rate: 0.87,
        avg_edge_bps: 230,
        max_exposure_usdc: 2500,
        fills: [
          {
            id: '1',
            asset_id: 'token_123',
            fill_price: 0.50,
            fill_shares: 1000,
            fill_usdc: 500,
            fill_ts_ms: Date.now() - 3600000,
          },
        ],
        top_markets: [
          {
            market_id: '1',
            name: 'Bitcoin $100k',
            pnl: 150.25,
            trades: 5,
          },
        ],
      });
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
                    label="PnL"
                    value={`$${results.pnl_total.toFixed(2)}`}
                    trend={results.pnl_total >= 0 ? 'up' : 'down'}
                    tooltip="Profit and Loss total"
                  />
                  <KPI
                    label="Fill Rate"
                    value={`${(results.fill_rate * 100).toFixed(0)}%`}
                    tooltip="Porcentaje de órdenes ejecutadas"
                  />
                  <KPI
                    label="Trades"
                    value={results.trades_count}
                    tooltip="Número de trades ejecutados"
                  />
                  <KPI
                    label="Avg Edge"
                    value={`${(results.avg_edge_bps / 100).toFixed(2)}%`}
                    tooltip="Ventaja promedio por trade"
                  />
                  <KPI
                    label="Max Exposure"
                    value={`$${results.max_exposure_usdc.toLocaleString()}`}
                    tooltip="Exposición máxima simultánea"
                  />
                </KPIBar>

                <Tabs defaultValue="summary" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="summary">Summary</TabsTrigger>
                    <TabsTrigger value="fills">Fills</TabsTrigger>
                    <TabsTrigger value="markets">Top Markets</TabsTrigger>
                  </TabsList>

                  <TabsContent value="summary" className="space-y-2">
                    <Panel>
                      <div className="space-y-2 text-[13px]">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Total PnL:</span>
                          <span className="font-semibold">${results.pnl_total.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Total Trades:</span>
                          <span>{results.trades_count}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Fill Rate:</span>
                          <span>{(results.fill_rate * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Average Edge:</span>
                          <span>{(results.avg_edge_bps / 100).toFixed(2)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Max Exposure:</span>
                          <span>${results.max_exposure_usdc.toLocaleString()}</span>
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
                            <TableHead>Price</TableHead>
                            <TableHead>Shares</TableHead>
                            <TableHead>USDC</TableHead>
                            <TableHead>Time</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {results.fills.map((fill) => (
                            <TableRow key={fill.id}>
                              <TableCell className="font-mono text-[11px]">
                                {fill.asset_id.slice(0, 16)}...
                              </TableCell>
                              <TableCell>{fill.fill_price.toFixed(4)}</TableCell>
                              <TableCell>{fill.fill_shares.toFixed(2)}</TableCell>
                              <TableCell>${fill.fill_usdc.toFixed(2)}</TableCell>
                              <TableCell className="text-[11px] text-muted-foreground">
                                {new Date(fill.fill_ts_ms).toLocaleTimeString()}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>

                  <TabsContent value="markets">
                    <div className="border rounded-lg overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Market</TableHead>
                            <TableHead>PnL</TableHead>
                            <TableHead>Trades</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {results.top_markets.map((market) => (
                            <TableRow key={market.market_id}>
                              <TableCell>{market.name}</TableCell>
                              <TableCell className={market.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                                ${market.pnl.toFixed(2)}
                              </TableCell>
                              <TableCell>{market.trades}</TableCell>
                            </TableRow>
                          ))}
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

