'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';

interface ValueSignal {
  id: string;
  edgeNet: number;
  edgeDelta: number;
  edgeHistory: Array<{ timestamp: number; edge: number }>;
}

interface EdgeDynamicsProps {
  value: ValueSignal;
}

export function EdgeDynamics({ value }: EdgeDynamicsProps) {
  const calculateVelocity = () => {
    if (value.edgeHistory.length < 2) return 0;
    const recent = value.edgeHistory.slice(-5);
    const changes = recent.slice(1).map((point, idx) => 
      point.edge - recent[idx].edge
    );
    const avgChange = changes.reduce((a, b) => a + b, 0) / changes.length;
    return avgChange;
  };

  const calculateVolatility = () => {
    if (value.edgeHistory.length < 2) return 0;
    const edges = value.edgeHistory.map(p => p.edge);
    const mean = edges.reduce((a, b) => a + b, 0) / edges.length;
    const variance = edges.reduce((sum, edge) => sum + Math.pow(edge - mean, 2), 0) / edges.length;
    return Math.sqrt(variance);
  };

  const velocity = calculateVelocity();
  const volatility = calculateVolatility();

  // Simple visualization - in a real app, you'd use a charting library
  const maxEdge = Math.max(...value.edgeHistory.map(p => p.edge));
  const minEdge = Math.min(...value.edgeHistory.map(p => p.edge));
  const range = maxEdge - minEdge || 1;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Edge Evolution
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Velocidad de Cambio</div>
            <div className={velocity > 0 ? 'text-green-600' : velocity < 0 ? 'text-red-600' : 'text-gray-600'}>
              <span className="text-lg font-semibold">
                {velocity > 0 ? '+' : ''}{velocity.toFixed(3)}%
              </span>
              <span className="text-xs ml-1">/min</span>
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Volatilidad</div>
            <div className="text-lg font-semibold">
              {volatility.toFixed(3)}%
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Rango (últimos 2min)</div>
            <div className="text-lg font-semibold">
              {minEdge.toFixed(2)}% - {maxEdge.toFixed(2)}%
            </div>
          </div>
        </div>

        {/* Simple timeline visualization */}
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">Timeline del Edge (últimos 2 minutos)</div>
          <div className="h-24 bg-muted rounded-lg p-2 relative">
            <div className="absolute inset-0 flex items-end justify-between px-2">
              {value.edgeHistory.map((point, idx) => {
                const height = ((point.edge - minEdge) / range) * 100;
                return (
                  <div
                    key={idx}
                    className="bg-primary rounded-t"
                    style={{
                      width: `${100 / value.edgeHistory.length}%`,
                      height: `${height}%`,
                      minHeight: '2px',
                    }}
                    title={`${point.edge.toFixed(2)}%`}
                  />
                );
              })}
            </div>
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{value.edgeHistory[0]?.timestamp != null
              ? new Date(value.edgeHistory[0].timestamp).toLocaleTimeString('es-ES', { minute: '2-digit', second: '2-digit' })
              : '--:--'}</span>
            <span>Ahora</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

