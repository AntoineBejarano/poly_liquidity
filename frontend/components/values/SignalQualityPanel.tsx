'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Shield, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

interface QualityMetrics {
  sourcesConfirming: number;
  historicalConsistency: number;
  invalidationRatio: number;
  contradictions: number;
}

interface ValueSignal {
  id: string;
  event: string;
  market: string;
  confidence: 'high' | 'medium' | 'low';
  quality: QualityMetrics;
}

interface SignalQualityPanelProps {
  values: ValueSignal[];
  selectedValue: ValueSignal | null;
}

export function SignalQualityPanel({ values, selectedValue }: SignalQualityPanelProps) {
  const getConfidenceLevel = (value: ValueSignal): 'high' | 'medium' | 'low' => {
    if (value.quality.contradictions > 0) return 'low';
    if (value.quality.sourcesConfirming >= 2 && value.quality.historicalConsistency > 0.8) return 'high';
    if (value.quality.sourcesConfirming >= 1 && value.quality.historicalConsistency > 0.6) return 'medium';
    return 'low';
  };

  const getConfidenceBadge = (confidence: 'high' | 'medium' | 'low') => {
    const variants: Record<string, { className: string; icon: React.ReactNode }> = {
      high: {
        className: 'bg-green-50 text-green-700 border-green-200',
        icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
      },
      medium: {
        className: 'bg-yellow-50 text-yellow-700 border-yellow-200',
        icon: <AlertTriangle className="h-3 w-3 mr-1" />,
      },
      low: {
        className: 'bg-red-50 text-red-700 border-red-200',
        icon: <XCircle className="h-3 w-3 mr-1" />,
      },
    };
    const config = variants[confidence];
    return (
      <Badge variant="outline" className={config.className}>
        {config.icon}
        {confidence.charAt(0).toUpperCase() + confidence.slice(1)} Confidence
      </Badge>
    );
  };

  const valuesToShow = selectedValue ? [selectedValue] : values;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Signal Quality
          {selectedValue && (
            <Badge variant="outline" className="ml-2">
              Filtrado: {selectedValue.event}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {valuesToShow.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground text-sm">
            No hay values disponibles
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Evento / Mercado</TableHead>
                <TableHead>Fuentes Confirmando</TableHead>
                <TableHead>Consistencia Histórica</TableHead>
                <TableHead>Ratio Invalidación</TableHead>
                <TableHead>Contradicciones</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {valuesToShow.map((value) => {
                const confidence = getConfidenceLevel(value);
                return (
                  <TableRow key={value.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-sm">{value.event}</div>
                        <div className="text-xs text-muted-foreground">{value.market}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold">{value.quality.sourcesConfirming}</div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-muted rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full"
                            style={{ width: `${value.quality.historicalConsistency * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {(value.quality.historicalConsistency * 100).toFixed(0)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={value.quality.invalidationRatio > 0.2 ? 'text-red-600' : 'text-green-600'}>
                        {(value.quality.invalidationRatio * 100).toFixed(1)}%
                      </span>
                    </TableCell>
                    <TableCell>
                      {value.quality.contradictions > 0 ? (
                        <Badge variant="destructive">{value.quality.contradictions}</Badge>
                      ) : (
                        <span className="text-green-600">0</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {getConfidenceBadge(confidence)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

