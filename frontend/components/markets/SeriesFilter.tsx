'use client';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';

interface Series {
  series_id: string;
  polymarket_series_id: string;
  name: string;
  slug: string | null;
  description: string | null;
  series_type: string | null;
  recurrence: string | null;
  markets_count: number;
}

interface SeriesFilterProps {
  series: Series[];
  selectedSeries: string;
  onSelectionChange: (seriesId: string) => void;
}

export function SeriesFilter({ series, selectedSeries, onSelectionChange }: SeriesFilterProps) {
  if (series.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <Label htmlFor="series-filter" className="text-xs font-medium text-foreground">
        Filtrar por Series
      </Label>
      <Select value={selectedSeries} onValueChange={onSelectionChange}>
        <SelectTrigger id="series-filter" className="w-full text-xs">
          <SelectValue placeholder="Todas las series" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Todas las series</SelectItem>
          {series.map((s) => (
            <SelectItem key={s.series_id} value={s.series_id}>
              {s.name} ({s.markets_count} markets)
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

