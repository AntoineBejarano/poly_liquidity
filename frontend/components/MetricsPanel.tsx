'use client';

import React, { memo } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip as RechartsTooltip, CartesianGrid, BarChart, Bar, PieChart, Pie, Cell, Legend } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CustomChartTooltip } from '@/components/charts/CustomChartTooltip';

interface PnLPoint { time: string; value: number }
interface LatencyPoint { stage: string; latency: number }
interface DecisionPoint { name: string; value: number }

export const MetricsPanel = memo(function MetricsPanel({
  pnl = [],
  latencyByStage = [],
  decisions = []
}: {
  pnl?: PnLPoint[];
  latencyByStage?: LatencyPoint[];
  decisions?: DecisionPoint[];
}) {
  // Fallback sample data if none provided
  const samplePnl = pnl.length ? pnl : [
    { time: '09:00', value: 0 },
    { time: '10:00', value: 1200 },
    { time: '11:00', value: 800 },
    { time: '12:00', value: 2000 },
    { time: '13:00', value: 1500 },
  ];

  const sampleLatency = latencyByStage.length ? latencyByStage : [
    { stage: 'SCAN', latency: 12 },
    { stage: 'STRATEGY', latency: 45 },
    { stage: 'RISK', latency: 30 },
    { stage: 'EXECUTION', latency: 120 },
  ];

  const sampleDecisions = decisions.length ? decisions : [
    { name: 'APPROVED', value: 120 },
    { name: 'REJECTED', value: 20 },
    { name: 'ADJUSTED', value: 8 },
  ];

  const COLORS = ['hsl(var(--chart-1))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))', 'hsl(var(--chart-4))', 'hsl(var(--chart-5))'];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">P&L (últimas horas)</CardTitle>
        </CardHeader>
        <CardContent>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={samplePnl}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="time"
                  className="text-xs"
                  stroke="hsl(var(--muted-foreground))"
                />
                <YAxis
                  className="text-xs"
                  stroke="hsl(var(--muted-foreground))"
                />
                <RechartsTooltip
                  content={<CustomChartTooltip valueFormatter={(v) => `$${v.toLocaleString()}`} />}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">Latencia por etapa (ms)</CardTitle>
        </CardHeader>
        <CardContent>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={sampleLatency} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  type="number"
                  className="text-xs"
                  stroke="hsl(var(--muted-foreground))"
                />
                <YAxis
                  dataKey="stage"
                  type="category"
                  className="text-xs"
                  stroke="hsl(var(--muted-foreground))"
                />
                <RechartsTooltip
                  content={<CustomChartTooltip valueFormatter={(v) => `${v}ms`} />}
                />
                <Bar dataKey="latency" fill="hsl(var(--chart-2))">
                  {sampleLatency.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">Distribución de decisiones</CardTitle>
        </CardHeader>
        <CardContent>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <PieChart>
                <RechartsTooltip
                  content={<CustomChartTooltip />}
                />
                <Legend
                  wrapperStyle={{ fontSize: '12px' }}
                />
                <Pie
                  data={sampleDecisions}
                  dataKey="value"
                  nameKey="name"
                  outerRadius={80}
                  fill="hsl(var(--chart-1))"
                >
                  {sampleDecisions.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});

MetricsPanel.displayName = 'MetricsPanel';

export default MetricsPanel;
