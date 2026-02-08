'use client';

import { TableHead } from '@/components/ui/table';
import { ChevronUp, ChevronDown, ArrowUpDown } from 'lucide-react';

interface SortableTableHeadProps {
  label: string;
  sortKey: string;
  currentSortBy: string | null;
  sortAsc: boolean;
  onSort: (key: string) => void;
}

export function SortableTableHead({ label, sortKey, currentSortBy, sortAsc, onSort }: SortableTableHeadProps) {
  const isActive = currentSortBy === sortKey;

  return (
    <TableHead>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className="flex items-center gap-1 hover:text-foreground transition-colors font-medium"
      >
        {label}
        {isActive ? (
          sortAsc ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )
        ) : (
          <ArrowUpDown className="h-4 w-4 text-muted-foreground/50" />
        )}
      </button>
    </TableHead>
  );
}
