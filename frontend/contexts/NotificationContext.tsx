'use client';

import React, { useCallback, useRef, useState } from 'react';
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
import { Button } from '@/components/ui/button';

export type ConfirmVariant = 'default' | 'danger';

export interface ConfirmOptions {
  title?: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
}

type Resolver = (value: boolean) => void;

const defaultOptions: Required<Omit<ConfirmOptions, 'description'>> = {
  title: 'Confirmar',
  confirmLabel: 'Aceptar',
  cancelLabel: 'Cancelar',
  variant: 'default',
};

const NotificationContext = React.createContext<{
  confirmDialog: (options: ConfirmOptions) => Promise<boolean>;
} | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions & { description: string }>({
    description: '',
    ...defaultOptions,
  });
  const resolveRef = useRef<Resolver | null>(null);

  const confirmDialog = useCallback((opts: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
      setOptions({
        ...defaultOptions,
        ...opts,
        description: opts.description,
      });
      setOpen(true);
    });
  }, []);

  const handleConfirm = useCallback(() => {
    resolveRef.current?.(true);
    resolveRef.current = null;
    setOpen(false);
  }, []);

  const handleCancel = useCallback(() => {
    resolveRef.current?.(false);
    resolveRef.current = null;
    setOpen(false);
  }, []);

  const handleOpenChange = useCallback(
    (isOpen: boolean) => {
      setOpen(isOpen);
      if (!isOpen) {
        resolveRef.current?.(false);
        resolveRef.current = null;
      }
    },
    []
  );

  return (
    <NotificationContext.Provider value={{ confirmDialog }}>
      {children}
      <AlertDialog open={open} onOpenChange={handleOpenChange}>
        <AlertDialogContent
          className="max-w-md rounded-2xl border border-border/80 bg-background shadow-xl backdrop-blur-sm"
          onPointerDownOutside={(e) => e.preventDefault()}
          onEscapeKeyDown={handleCancel}
        >
          <AlertDialogHeader>
            <AlertDialogTitle className="text-lg font-semibold text-foreground">
              {options.title}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm text-muted-foreground leading-relaxed">
              {options.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex gap-2 sm:gap-2 mt-4">
            <AlertDialogCancel asChild>
              <Button type="button" variant="outline" onClick={handleCancel} className="rounded-xl">
                {options.cancelLabel}
              </Button>
            </AlertDialogCancel>
            <AlertDialogAction asChild>
              <Button
                type="button"
                variant={options.variant === 'danger' ? 'destructive' : 'default'}
                onClick={handleConfirm}
                className="rounded-xl"
              >
                {options.confirmLabel}
              </Button>
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </NotificationContext.Provider>
  );
}

export function useConfirmDialog() {
  const ctx = React.useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useConfirmDialog must be used within NotificationProvider');
  }
  return ctx;
}
