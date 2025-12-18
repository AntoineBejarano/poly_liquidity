'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { History } from 'lucide-react';

interface HistoricalData {
  timesDetectedToday: number;
  avgDuration: number;
  executablePercent: number;
  profitablePercent?: number;
}

interface ValueSignal {
  id: string;
  event: string;
  market: string;
  historical: HistoricalData;
}

interface HistoricalContextProps {
  value: ValueSignal;
}

export function HistoricalContext({ value }: HistoricalContextProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Historical Snapshot
          <Badge variant="outline" className="ml-2">
            {value.event}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Veces Detectada Hoy</div>
            <div className="text-2xl font-bold">{value.historical.timesDetectedToday}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Duración Media</div>
            <div className="text-2xl font-bold">
              {Math.floor(value.historical.avgDuration / 60)}m {value.historical.avgDuration % 60}s
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">% Ejecutable</div>
            <div className="text-2xl font-bold text-green-600">
              {value.historical.executablePercent}%
            </div>
          </div>
          {value.historical.profitablePercent !== undefined && (
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">% Rentable</div>
              <div className={value.historical.profitablePercent > 50 ? 'text-2xl font-bold text-green-600' : 'text-2xl font-bold text-yellow-600'}>
                {value.historical.profitablePercent}%
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

