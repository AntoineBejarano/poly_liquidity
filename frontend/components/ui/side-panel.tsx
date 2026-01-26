'use client';

import { X } from 'lucide-react';
import { Button } from './button';
import { cn } from '@/lib/utils';

interface SidePanelProps {
  open: boolean;
  onClose: () => void;
  position?: 'left' | 'right';
  width?: string;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function SidePanel({ 
  open, 
  onClose, 
  position = 'right', 
  width = 'w-80',
  title,
  children,
  className 
}: SidePanelProps) {
  if (!open) return null;

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />
      
      {/* Panel */}
      <div
        className={cn(
          "fixed top-0 bottom-0 z-50 bg-card border-l border-border shadow-lg overflow-y-auto",
          position === 'right' ? 'right-0' : 'left-0',
          width,
          className
        )}
      >
        {title && (
          <div className="sticky top-0 bg-card border-b border-border px-3 py-2 flex items-center justify-between z-10">
            <h3 className="text-sm font-semibold">{title}</h3>
            <Button
              variant="ghost"
              size="compact-sm"
              onClick={onClose}
              className="h-6 w-6 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}
        <div className="p-3">
          {children}
        </div>
      </div>
    </>
  );
}

