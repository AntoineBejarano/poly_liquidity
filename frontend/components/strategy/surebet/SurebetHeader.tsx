'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Strategy } from '@/types/strategy';
import { Pause, Square, Settings, AlertTriangle } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { useState } from 'react';
import Link from 'next/link';

interface SurebetHeaderProps {
  strategy: Strategy;
  globalStatus: 'in_sync' | 'latency_risk' | 'execution_halted';
  venueAWallet?: string;
  venueBConnection?: string;
  onPause?: () => void;
  onResume?: () => void;
  onEmergencyStop?: () => void;
  onConfig?: () => void;
  isLoading?: boolean;
}

export function SurebetHeader({
  strategy,
  globalStatus,
  venueAWallet,
  venueBConnection,
  onPause,
  onResume,
  onEmergencyStop,
  onConfig,
  isLoading = false,
}: SurebetHeaderProps) {
  const [showEmergencyDialog, setShowEmergencyDialog] = useState(false);

  const getGlobalStatusBadge = () => {
    switch (globalStatus) {
      case 'in_sync':
        return <Badge variant="success" className="flex items-center gap-1">🟢 In Sync</Badge>;
      case 'latency_risk':
        return <Badge variant="warning" className="flex items-center gap-1">🟡 Latency Risk</Badge>;
      case 'execution_halted':
        return <Badge variant="error" className="flex items-center gap-1">🔴 Execution Halted</Badge>;
    }
  };

  return (
    <div className="space-y-4 w-full">
      {/* Breadcrumb */}
      <Link 
        href="/dashboard" 
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 w-fit"
      >
        ← Volver al Dashboard
      </Link>

      {/* Header Principal */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-foreground leading-tight break-words">{strategy.name}</h1>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span className="text-sm text-muted-foreground">Template: Surebet</span>
            <span className="text-sm text-muted-foreground">•</span>
            <span className="text-sm text-muted-foreground">
              Venue A: Polymarket {venueAWallet && `(${venueAWallet.slice(0, 8)}...)`}
            </span>
            <span className="text-sm text-muted-foreground">•</span>
            <span className="text-sm text-muted-foreground">
              Venue B: Pinnacle {venueBConnection && `(API)`}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
          {getGlobalStatusBadge()}
        </div>
      </div>

      {/* Controles */}
      <div className="flex items-center gap-2 flex-wrap">
        {strategy.is_active ? (
          <>
            <Button
              variant="outline"
              onClick={onPause}
              disabled={isLoading}
            >
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
            {onResume && (
              <Button
                variant="outline"
                onClick={onResume}
                disabled={isLoading}
              >
                Resume
              </Button>
            )}
            <AlertDialog open={showEmergencyDialog} onOpenChange={setShowEmergencyDialog}>
              <AlertDialogTrigger asChild>
                <Button
                  variant="destructive"
                  disabled={isLoading}
                >
                  <Square className="h-4 w-4 mr-2" />
                  Emergency Stop
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Emergency Stop</AlertDialogTitle>
                  <AlertDialogDescription>
                    Esta acción detendrá inmediatamente todas las ejecuciones y cerrará todas las posiciones abiertas.
                    Esta es una acción de emergencia para situaciones críticas.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => {
                      if (onEmergencyStop) {
                        onEmergencyStop();
                      }
                      setShowEmergencyDialog(false);
                    }}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Emergency Stop
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        ) : (
          <Button
            onClick={onResume}
            disabled={isLoading}
          >
            Iniciar
          </Button>
        )}
        <Button
          variant="outline"
          onClick={onConfig}
          disabled={isLoading}
        >
          <Settings className="h-4 w-4 mr-2" />
          Configurar
        </Button>
      </div>
    </div>
  );
}

