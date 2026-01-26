'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, Clock, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CheckerStatus {
  id: string;
  name: string;
  source: string; // Binance, ESPN, etc.
  lastUpdate: string; // timestamp
  latency?: number; // ms
  status: 'confirmed' | 'pending' | 'delayed' | 'error';
  delay?: number; // seconds
}

interface ExternalConfirmationStatusProps {
  checkers: CheckerStatus[];
}

export function ExternalConfirmationStatus({ checkers }: ExternalConfirmationStatusProps) {
  if (checkers.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Estado de Confirmación Externa</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No hay checkers configurados para esta estrategia.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Estado de Confirmación Externa</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {checkers.map((checker) => (
            <div key={checker.id} className="border rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{checker.name}</span>
                  <Badge variant="outline" className="text-xs">
                    {checker.source}
                  </Badge>
                </div>
                <StatusBadge 
                  status={
                    checker.status === 'confirmed' ? 'ok' :
                    checker.status === 'pending' ? 'degraded' : 'error'
                  }
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Último update</div>
                  <div className="font-medium">{checker.lastUpdate}</div>
                </div>
                {checker.latency !== undefined && (
                  <div>
                    <div className="text-xs text-muted-foreground">Latencia</div>
                    <div className={cn(
                      "font-medium",
                      checker.latency < 1000 ? "text-green-600" :
                      checker.latency < 5000 ? "text-yellow-600" : "text-red-600"
                    )}>
                      {checker.latency}ms
                    </div>
                  </div>
                )}
              </div>

              {checker.status === 'delayed' && checker.delay && (
                <Alert variant="warning">
                  <Clock className="h-4 w-4" />
                  <AlertDescription>
                    Delay detectado: {checker.delay}s (más allá del umbral permitido)
                  </AlertDescription>
                </Alert>
              )}

              {checker.status === 'error' && (
                <Alert variant="destructive">
                  <XCircle className="h-4 w-4" />
                  <AlertDescription>
                    Error en la conexión con {checker.source}. Verificar configuración.
                  </AlertDescription>
                </Alert>
              )}

              {checker.status === 'confirmed' && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Confirmado - Señal confiable</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

