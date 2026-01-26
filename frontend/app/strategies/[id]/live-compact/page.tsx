'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { StatusPill } from '@/components/ui/status-pill';
import { MetricChip } from '@/components/ui/metric-chip';
import { KPIBar, KPI } from '@/components/ui/kpi-bar';
import { Panel } from '@/components/ui/panel';
import { Badge } from '@/components/ui/badge';
import { Play, Pause, Square, BarChart3 } from 'lucide-react';

interface MarketEvent {
  event_id: string;
  name: string;
  status: 'In Play' | 'Finished' | 'Resolved';
  confirmed: boolean;
  confidence?: number;
  best_bid: number;
  best_ask: number;
  spread_bps: number;
  liquidity: number;
  impact: number;
  freshness: number;
  last_action: string;
  pnl?: number;
}

export default function StrategyLiveCompactPage() {
  const params = useParams();
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyId = params.id as string;

  const [isActive, setIsActive] = useState(true);
  const [capitalUsed, setCapitalUsed] = useState(2500);
  const [maxCapital] = useState(5000);
  const [exposure, setExposure] = useState(1200);

  // Mock data para demo
  const events: MarketEvent[] = [
    {
      event_id: '1',
      name: 'Will Bitcoin reach $100k by end of 2024?',
      status: 'Finished',
      confirmed: true,
      confidence: 0.95,
      best_bid: 0.50,
      best_ask: 0.52,
      spread_bps: 150,
      liquidity: 2500,
      impact: 30,
      freshness: 1.2,
      last_action: 'Plan Created',
      pnl: 234.56,
    },
    {
      event_id: '2',
      name: 'Will Ethereum reach $5000?',
      status: 'In Play',
      confirmed: false,
      confidence: 0.75,
      best_bid: 0.48,
      best_ask: 0.51,
      spread_bps: 200,
      liquidity: 1800,
      impact: 45,
      freshness: 0.8,
      last_action: 'Precheck Failed',
    },
  ];

  const handleSimulate = () => {
    router.push(`/strategies/${strategyId}/simulate`);
  };

  const handlePlay = async () => {
    if (!user || !stackApp) return;
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/strategies/${strategyId}/activate`);
      setIsActive(true);
    } catch (err) {
      console.error('Error activating:', err);
    }
  };

  const handlePause = async () => {
    if (!user || !stackApp) return;
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/strategies/${strategyId}/deactivate`);
      setIsActive(false);
    } catch (err) {
      console.error('Error pausing:', err);
    }
  };

  const handleStop = async () => {
    if (!user || !stackApp) return;
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/strategies/${strategyId}/deactivate`);
      setIsActive(false);
    } catch (err) {
      console.error('Error stopping:', err);
    }
  };

  const getSpreadColor = (spread: number): 'green' | 'yellow' | 'red' => {
    if (spread < 100) return 'green';
    if (spread < 200) return 'yellow';
    return 'red';
  };

  const getFreshnessColor = (freshness: number): 'green' | 'yellow' | 'red' => {
    if (freshness < 1) return 'green';
    if (freshness < 2) return 'yellow';
    return 'red';
  };

  return (
    <Layout>
      <div className="flex flex-col h-[calc(100vh-120px)]">
        {/* Topbar compacto */}
        <div className="flex items-center justify-between px-3 py-2 border-b bg-card flex-shrink-0">
          <div className="flex items-center gap-3">
            <StatusPill status={isActive ? 'active' : 'paused'} />
            <span className="text-[13px]">Capital: ${capitalUsed.toLocaleString()}/${maxCapital.toLocaleString()}</span>
            <span className="text-[13px]">Exposure: ${exposure.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button size="compact" variant="outline" onClick={handleSimulate}>
              <BarChart3 className="h-3 w-3 mr-1" />
              Simulate
            </Button>
            <Button size="compact" onClick={handlePlay} disabled={isActive}>
              <Play className="h-3 w-3 mr-1" />
              Play
            </Button>
            <Button size="compact" variant="outline" onClick={handlePause} disabled={!isActive}>
              <Pause className="h-3 w-3 mr-1" />
              Pause
            </Button>
            <Button size="compact-sm" variant="destructive" onClick={handleStop}>
              <Square className="h-3 w-3 mr-1" />
              Stop
            </Button>
          </div>
        </div>

        {/* Main split */}
        <div className="flex flex-1 overflow-hidden">
          {/* Tabla izquierda (70%) */}
          <div className="flex-[0.7] overflow-auto border-r">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Confirmed</TableHead>
                  <TableHead>Best Price</TableHead>
                  <TableHead>Spread</TableHead>
                  <TableHead>Liquidity</TableHead>
                  <TableHead>Impact</TableHead>
                  <TableHead>Freshness</TableHead>
                  <TableHead>Last Action</TableHead>
                  <TableHead>PnL</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.map((event) => (
                  <TableRow key={event.event_id}>
                    <TableCell>
                      <div className="max-w-[200px]">
                        <span className="text-[13px] font-medium truncate block">{event.name}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[11px]">
                        {event.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {event.confirmed ? (
                          <>
                            <span className="text-green-600">✅</span>
                            {event.confidence && (
                              <span className="text-[11px] text-muted-foreground">
                                {(event.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-muted-foreground">❌</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-[13px] font-mono">
                        {event.best_bid.toFixed(2)} / {event.best_ask.toFixed(2)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <MetricChip
                        label=""
                        value={`${event.spread_bps} bps`}
                        color={getSpreadColor(event.spread_bps)}
                        tooltip="Diferencia entre mejor bid y ask. Spread bajo = más liquidez."
                      />
                    </TableCell>
                    <TableCell>
                      <MetricChip
                        label=""
                        value={`$${(event.liquidity / 1000).toFixed(1)}k`}
                        tooltip="Liquidez disponible a 50bps del mejor precio"
                      />
                    </TableCell>
                    <TableCell>
                      <MetricChip
                        label=""
                        value={`${event.impact} bps`}
                        tooltip="Impacto en precio al ejecutar $1000"
                      />
                    </TableCell>
                    <TableCell>
                      <MetricChip
                        label=""
                        value={`${event.freshness.toFixed(1)}s`}
                        color={getFreshnessColor(event.freshness)}
                        tooltip="Tiempo desde última actualización del orderbook"
                      />
                    </TableCell>
                    <TableCell>
                      <span className="text-[13px]">{event.last_action}</span>
                    </TableCell>
                    <TableCell>
                      {event.pnl !== undefined && (
                        <span className={`text-[13px] font-medium ${event.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ${event.pnl.toFixed(2)}
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Panel derecho (30%) */}
          <div className="flex-[0.3] overflow-auto p-3 space-y-2">
            <Panel>
              <h4 className="text-sm font-semibold mb-2">Orderbook Health</h4>
              <div className="space-y-2 text-[13px]">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">WS:</span>
                  <Badge variant="outline" className="text-[11px]">✅ Connected</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Freshness p95:</span>
                  <span>1.2s</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Update Rate:</span>
                  <span>5.3 Hz</span>
                </div>
              </div>
            </Panel>

            <Panel>
              <h4 className="text-sm font-semibold mb-2">Precheck Failures</h4>
              <div className="space-y-1 text-[13px]">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Book Stale:</span>
                  <span>2</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Price Changed:</span>
                  <span>1</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Impact Too High:</span>
                  <span>0</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Timeout:</span>
                  <span>0</span>
                </div>
              </div>
            </Panel>

            <Panel>
              <h4 className="text-sm font-semibold mb-2">Recent Orders</h4>
              <div className="space-y-2 text-[13px]">
                <div className="flex items-center justify-between border-b pb-2">
                  <div>
                    <div className="font-mono text-[11px]">#12345</div>
                    <div className="text-muted-foreground">FILLED</div>
                  </div>
                  <div className="text-right">
                    <div>$1,000</div>
                    <div className="text-muted-foreground text-[11px]">2m ago</div>
                  </div>
                </div>
                <div className="flex items-center justify-between border-b pb-2">
                  <div>
                    <div className="font-mono text-[11px]">#12346</div>
                    <div className="text-muted-foreground">PENDING</div>
                  </div>
                  <div className="text-right">
                    <div>$500</div>
                    <div className="text-muted-foreground text-[11px]">1m ago</div>
                  </div>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </Layout>
  );
}

