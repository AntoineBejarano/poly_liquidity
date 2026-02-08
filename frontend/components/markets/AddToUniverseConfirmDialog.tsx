'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import type { DiscoveryTradeableMarket } from '@/lib/discovery/types';

export interface AddToUniverseConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  market: DiscoveryTradeableMarket | null;
  strategyName: string;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
}

export function AddToUniverseConfirmDialog({
  open,
  onOpenChange,
  market,
  strategyName,
  onConfirm,
  loading = false,
}: AddToUniverseConfirmDialogProps) {
  const handleConfirm = async () => {
    await onConfirm();
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Añadir al universo</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-2 pt-2">
              <p>¿Añadir este mercado al universo de la estrategia <strong>{strategyName}</strong>?</p>
              {market && (
                <p className="text-sm text-muted-foreground line-clamp-3 border-l-2 border-muted pl-3">
                  {market.question}
                </p>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={(e) => { e.preventDefault(); handleConfirm(); }} disabled={loading}>
            {loading ? 'Añadiendo...' : 'Añadir'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
