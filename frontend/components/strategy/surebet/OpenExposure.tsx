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
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, Clock, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExposureItem {
  id: string;
  eventName: string;
  netExposure: number;
  polymarketExposure: number;
  pinnacleExposure: number;
  directionalRisk: 'balanced' | 'polymarket_heavy' | 'pinnacle_heavy' | 'unhedged';
  timeSinceImbalance?: number; // seconds
}

interface OpenExposureProps {
  exposures: ExposureItem[];
  onForceHedge?: (id: string) => void;
  onClosePosition?: (id: string) => void;
  onFreezeEvent?: (id: string) => void;
}

export function OpenExposure({ 
  exposures, 
  onForceHedge, 
  onClosePosition, 
  onFreezeEvent 
}: OpenExposureProps) {
  const getRiskBadge = (risk: ExposureItem['directionalRisk']) => {
    switch (risk) {
      case 'balanced':
        return <Badge variant="success">Balanced</Badge>;
      case 'polymarket_heavy':
        return <Badge variant="warning">PM Heavy</Badge>;
      case 'pinnacle_heavy':
        return <Badge variant="warning">PN Heavy</Badge>;
      case 'unhedged':
        return <Badge variant="error">Unhedged</Badge>;
    }
  };

  const totalNetExposure = exposures.reduce((sum, exp) => sum + exp.netExposure, 0);
  const unhedgedCount = exposures.filter(e => e.directionalRisk === 'unhedged').length;

  if (exposures.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Open Exposure
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay exposición abierta.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Open Exposure
          {unhedgedCount > 0 && (
            <Badge variant="error" className="ml-2">
              {unhedgedCount} unhedged
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {unhedgedCount > 0 && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {unhedgedCount} evento(s) sin hedge. Riesgo de exposición direccional.
            </AlertDescription>
          </Alert>
        )}

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Evento</TableHead>
                <TableHead>Exposición Neta</TableHead>
                <TableHead>PM Exposure</TableHead>
                <TableHead>PN Exposure</TableHead>
                <TableHead>Riesgo</TableHead>
                <TableHead>Tiempo Desbalance</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {exposures.map((exp) => (
                <TableRow key={exp.id}>
                  <TableCell className="font-medium">{exp.eventName}</TableCell>
                  <TableCell>
                    <span className={cn(
                      "font-semibold",
                      Math.abs(exp.netExposure) < 100 ? "text-green-600" :
                      Math.abs(exp.netExposure) < 500 ? "text-yellow-600" : "text-red-600"
                    )}>
                      ${exp.netExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </TableCell>
                  <TableCell>
                    ${exp.polymarketExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </TableCell>
                  <TableCell>
                    ${exp.pinnacleExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </TableCell>
                  <TableCell>{getRiskBadge(exp.directionalRisk)}</TableCell>
                  <TableCell>
                    {exp.timeSinceImbalance !== undefined && exp.timeSinceImbalance > 0 ? (
                      <span className={cn(
                        "text-sm flex items-center gap-1",
                        exp.timeSinceImbalance < 60 ? "text-green-600" :
                        exp.timeSinceImbalance < 300 ? "text-yellow-600" : "text-red-600"
                      )}>
                        <Clock className="h-3 w-3" />
                        {exp.timeSinceImbalance}s
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {exp.directionalRisk !== 'balanced' && onForceHedge && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onForceHedge(exp.id)}
                          className="text-xs"
                        >
                          Force Hedge
                        </Button>
                      )}
                      {onClosePosition && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onClosePosition(exp.id)}
                          className="text-xs"
                        >
                          Close
                        </Button>
                      )}
                      {onFreezeEvent && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onFreezeEvent(exp.id)}
                          className="text-xs"
                        >
                          Freeze
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <div className="pt-4 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Exposición neta total:</span>
            <span className={cn(
              "text-lg font-bold",
              Math.abs(totalNetExposure) < 1000 ? "text-green-600" :
              Math.abs(totalNetExposure) < 5000 ? "text-yellow-600" : "text-red-600"
            )}>
              ${totalNetExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

