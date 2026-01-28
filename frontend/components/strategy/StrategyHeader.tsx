'use client';

import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { Strategy } from '@/types/strategy';
import { Pause, Square, Settings, BarChart3, FileText, ArrowLeft, Play, Loader2 } from 'lucide-react';
import Link from 'next/link';
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

interface StrategyHeaderProps {
  strategy: Strategy;
  onPause?: () => void;
  onStop?: () => void;
  onActivate?: () => void;
  onConfig?: () => void;
  isLoading?: boolean;
}

export function StrategyHeader({ 
  strategy, 
  onPause, 
  onStop, 
  onConfig,
  isLoading = false 
}: StrategyHeaderProps) {
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  const getStatus = (): 'running' | 'paused' | 'error' | 'degraded' => {
    if (strategy.is_active) {
      return 'running';
    }
    if (strategy.disabled_at) {
      return 'error';
    }
    return 'paused';
  };

  const handleStop = () => {
    if (confirmText === strategy.name && onStop) {
      onStop();
      setShowStopDialog(false);
      setConfirmText('');
    }
  };

  return (
    <div className="space-y-4 w-full">
      {/* Breadcrumb */}
      <Link 
        href="/dashboard" 
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 w-fit"
      >
        <ArrowLeft className="h-4 w-4 flex-shrink-0" />
        <span>Volver al Dashboard</span>
      </Link>

      {/* Header Principal */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-foreground leading-tight break-words">{strategy.name}</h1>
          {strategy.description && (
            <p className="text-sm text-muted-foreground mt-1 break-words">
              {strategy.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
          <StatusBadge status={getStatus()} />
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            Última actualización: {strategy.updated_at 
              ? new Date(strategy.updated_at).toLocaleTimeString('es-ES')
              : 'N/A'}
          </span>
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
              Pausar
            </Button>
            <AlertDialog open={showStopDialog} onOpenChange={setShowStopDialog}>
              <AlertDialogTrigger asChild>
                <Button
                  variant="destructive"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Deteniendo...
                    </>
                  ) : (
                    <>
                      <Square className="h-4 w-4 mr-2" />
                      Detener
                    </>
                  )}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Esta acción detendrá completamente la estrategia. Para reactivarla, 
                    deberás iniciarla manualmente nuevamente.
                    <br /><br />
                    Escribe el nombre de la estrategia para confirmar: <strong>{strategy.name}</strong>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <div className="py-4">
                  <input
                    type="text"
                    value={confirmText}
                    onChange={(e) => setConfirmText(e.target.value)}
                    placeholder={strategy.name}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <AlertDialogFooter>
                  <AlertDialogCancel onClick={() => setConfirmText('')}>
                    Cancelar
                  </AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleStop}
                    disabled={confirmText !== strategy.name}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Detener Estrategia
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        ) : (
          <Button
            onClick={onActivate}
            disabled={isLoading}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Activando...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Activar
              </>
            )}
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
        <Button
          variant="outline"
          asChild
        >
          <Link href={`/strategies/${strategy.id}?tab=metrics`}>
            <BarChart3 className="h-4 w-4 mr-2" />
            Métricas
          </Link>
        </Button>
        <Button
          variant="outline"
          asChild
        >
          <Link href={`/strategies/${strategy.id}?tab=logs`}>
            <FileText className="h-4 w-4 mr-2" />
            Logs
          </Link>
        </Button>
      </div>
    </div>
  );
}

