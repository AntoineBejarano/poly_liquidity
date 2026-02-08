'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import type { AddScope } from '@/lib/discovery/types';

interface AddConfirmModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  scope: AddScope;
  refId: string;
  title: string;
  marketsCount: number;
  strategyName: string;
  loading?: boolean;
}

export function AddConfirmModal({
  open,
  onClose,
  onConfirm,
  scope,
  refId,
  title,
  marketsCount,
  strategyName,
  loading = false,
}: AddConfirmModalProps) {
  const scopeLabel =
    scope === 'market' ? 'Mercado' : scope === 'event' ? 'Evento' : 'Serie';

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Añadir a estrategia</DialogTitle>
          <DialogDescription>
            Confirmar que quieres añadir el siguiente alcance a la estrategia seleccionada.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-muted-foreground">Alcance: </span>
            <span className="font-medium">{scopeLabel}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Título: </span>
            <span className="font-medium">{title}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Markets a añadir: </span>
            <span className="font-medium">{marketsCount}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Estrategia: </span>
            <span className="font-medium">{strategyName}</span>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={onConfirm} disabled={loading}>
            {loading ? 'Añadiendo…' : 'Confirmar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
