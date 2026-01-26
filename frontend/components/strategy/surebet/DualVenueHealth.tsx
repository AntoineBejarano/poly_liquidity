'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, Clock, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VenueHealth {
  venue: 'polymarket' | 'pinnacle';
  name: string;
  status: 'connected' | 'degraded' | 'error' | 'stale';
  latency?: number; // ms
  lastPriceUpdate?: string;
  orderAcceptanceStatus?: 'ok' | 'limited' | 'error';
  oddsAge?: number; // seconds
  apiRateLimitStatus?: 'ok' | 'warning' | 'limited';
}

interface DualVenueHealthProps {
  venueA: VenueHealth;
  venueB: VenueHealth;
}

export function DualVenueHealth({ venueA, venueB }: DualVenueHealthProps) {
  const getStatusBadge = (status: VenueHealth['status']) => {
    switch (status) {
      case 'connected':
        return <StatusBadge status="ok" />;
      case 'degraded':
      case 'stale':
        return <StatusBadge status="degraded" />;
      case 'error':
        return <StatusBadge status="error" />;
    }
  };

  const getStatusColor = (status: VenueHealth['status']) => {
    switch (status) {
      case 'connected':
        return 'text-green-600';
      case 'degraded':
      case 'stale':
        return 'text-yellow-600';
      case 'error':
        return 'text-red-600';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Dual Venue Health</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Venue A - Polymarket */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-base">Venue A – Polymarket</h3>
              {getStatusBadge(venueA.status)}
            </div>
            
            <div className="space-y-3">
              {venueA.latency !== undefined && (
                <div>
                  <div className="text-xs text-muted-foreground">Latencia media</div>
                  <div className={cn(
                    "text-sm font-semibold",
                    venueA.latency < 500 ? "text-green-600" :
                    venueA.latency < 1000 ? "text-yellow-600" : "text-red-600"
                  )}>
                    {venueA.latency}ms
                  </div>
                </div>
              )}
              
              {venueA.lastPriceUpdate && (
                <div>
                  <div className="text-xs text-muted-foreground">Último price update</div>
                  <div className="text-sm font-medium">{venueA.lastPriceUpdate}</div>
                </div>
              )}
              
              {venueA.orderAcceptanceStatus && (
                <div>
                  <div className="text-xs text-muted-foreground">Order acceptance</div>
                  <Badge 
                    variant={
                      venueA.orderAcceptanceStatus === 'ok' ? 'success' :
                      venueA.orderAcceptanceStatus === 'limited' ? 'warning' : 'error'
                    }
                  >
                    {venueA.orderAcceptanceStatus === 'ok' ? 'OK' :
                     venueA.orderAcceptanceStatus === 'limited' ? 'Limited' : 'Error'}
                  </Badge>
                </div>
              )}
            </div>

            {venueA.status === 'error' && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  Error de conexión con Polymarket. Verificar configuración.
                </AlertDescription>
              </Alert>
            )}

            {venueA.status === 'degraded' && (
              <Alert variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Conexión degradada. Latencia elevada detectada.
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Venue B - Pinnacle */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-base">Venue B – Pinnacle</h3>
              {getStatusBadge(venueB.status)}
            </div>
            
            <div className="space-y-3">
              {venueB.latency !== undefined && (
                <div>
                  <div className="text-xs text-muted-foreground">Latencia</div>
                  <div className={cn(
                    "text-sm font-semibold",
                    venueB.latency < 1000 ? "text-green-600" :
                    venueB.latency < 2000 ? "text-yellow-600" : "text-red-600"
                  )}>
                    {venueB.latency}ms
                  </div>
                </div>
              )}
              
              {venueB.oddsAge !== undefined && (
                <div>
                  <div className="text-xs text-muted-foreground">Edad de las odds</div>
                  <div className={cn(
                    "text-sm font-semibold flex items-center gap-1",
                    venueB.oddsAge < 5 ? "text-green-600" :
                    venueB.oddsAge < 10 ? "text-yellow-600" : "text-red-600"
                  )}>
                    {venueB.oddsAge}s
                    {venueB.oddsAge > 10 && <Clock className="h-3 w-3" />}
                  </div>
                </div>
              )}
              
              {venueB.apiRateLimitStatus && (
                <div>
                  <div className="text-xs text-muted-foreground">API rate-limit</div>
                  <Badge 
                    variant={
                      venueB.apiRateLimitStatus === 'ok' ? 'success' :
                      venueB.apiRateLimitStatus === 'warning' ? 'warning' : 'error'
                    }
                  >
                    {venueB.apiRateLimitStatus === 'ok' ? 'OK' :
                     venueB.apiRateLimitStatus === 'warning' ? 'Warning' : 'Limited'}
                  </Badge>
                </div>
              )}
            </div>

            {venueB.status === 'error' && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  Error de conexión con Pinnacle. Verificar API.
                </AlertDescription>
              </Alert>
            )}

            {venueB.status === 'stale' && (
              <Alert variant="warning">
                <Clock className="h-4 w-4" />
                <AlertDescription>
                  Odds stale ({venueB.oddsAge}s). Ejecución bloqueada.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

