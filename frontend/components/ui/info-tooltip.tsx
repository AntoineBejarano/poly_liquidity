'use client';

import { useState } from 'react';
import { Info } from 'lucide-react';
import * as VisuallyHidden from '@radix-ui/react-visually-hidden';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface InfoTooltipProps {
  content: string;
  title?: string;
  className?: string;
}

export function InfoTooltip({ content, title, className }: InfoTooltipProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`inline-flex items-center justify-center ${className || ''}`}
        aria-label="Más información"
      >
        <Info className="h-3 w-3 text-muted-foreground cursor-help" />
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            {title ? (
              <DialogTitle>{title}</DialogTitle>
            ) : (
              <VisuallyHidden.Root>
                <DialogTitle>Más información</DialogTitle>
              </VisuallyHidden.Root>
            )}
            <DialogDescription className="text-[13px]">
              {content}
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    </>
  );
}

