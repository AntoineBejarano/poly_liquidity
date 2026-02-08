'use client';

import { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { DiscoveryMarket } from '@/lib/discovery/types';

interface MarketsTableViewProps {
  markets: DiscoveryMarket[];
  pagination: { hasMore: boolean; offset: number; limit: number };
  onPagePrev: () => void;
  onPageNext: () => void;
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  onAddMarket: (market: DiscoveryMarket) => void;
  onSelectMarket: (market: DiscoveryMarket | null) => void;
  addingId: string | null;
  orderbookMetrics?: Record<string, { spread_bps?: number; depth_usdc_at_50bps?: number }>;
}

export function MarketsTableView({
  markets,
  pagination,
  onPagePrev,
  onPageNext,
  selectedIds,
  onSelectionChange,
  onAddMarket,
  onSelectMarket,
  addingId,
  orderbookMetrics = {},
}: MarketsTableViewProps) {
  const allSelected = markets.length > 0 && markets.every((m) => selectedIds.has(m.polymarket_id));
  const someSelected = markets.some((m) => selectedIds.has(m.polymarket_id));

  const toggleAll = () => {
    if (allSelected) {
      const next = new Set(selectedIds);
      markets.forEach((m) => next.delete(m.polymarket_id));
      onSelectionChange(next);
    } else {
      const next = new Set(selectedIds);
      markets.forEach((m) => next.add(m.polymarket_id));
      onSelectionChange(next);
    }
  };

  const toggleOne = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  };

  const getSpread = (m: DiscoveryMarket) => {
    if (m.spread != null) return `${Math.round(m.spread)} bps`;
    const tok = m.clob_token_ids?.primary ?? m.clob_token_ids?.primary_yes;
    if (tok) {
      const ob = orderbookMetrics[tok];
      if (ob?.spread_bps != null) return `${Math.round(ob.spread_bps)} bps`;
    }
    return '—';
  };

  const getLiquidity = (m: DiscoveryMarket) => {
    const tok = m.clob_token_ids?.primary ?? m.clob_token_ids?.primary_yes;
    if (tok) {
      const ob = orderbookMetrics[tok];
      if (ob?.depth_usdc_at_50bps != null && ob.depth_usdc_at_50bps > 0)
        return `$${(ob.depth_usdc_at_50bps / 1000).toFixed(1)}k`;
    }
    return '—';
  };

  return (
    <div className="space-y-2">
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={allSelected ? true : someSelected ? 'indeterminate' : false}
                  onCheckedChange={toggleAll}
                  aria-label="Seleccionar todos"
                />
              </TableHead>
              <TableHead>Market</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Spread</TableHead>
              <TableHead>Liquidity</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {markets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  No hay mercados con estos filtros.
                </TableCell>
              </TableRow>
            ) : (
              markets.map((market) => {
                const mid = market.polymarket_id ?? market.market_id;
                const isAdding = addingId === mid;
                return (
                  <TableRow
                    key={mid}
                    className="cursor-pointer"
                    onClick={() => onSelectMarket(market)}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedIds.has(mid)}
                        onCheckedChange={() => toggleOne(mid)}
                        aria-label={`Seleccionar ${market.name}`}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium text-sm">{market.name}</span>
                        {(market.event_title || market.series_name) && (
                          <span className="text-xs text-muted-foreground">
                            {[market.event_title, market.series_name].filter(Boolean).join(' · ')}
                          </span>
                        )}
                        {market.tags?.length > 0 && (
                          <div className="flex gap-1 flex-wrap mt-0.5">
                            {market.tags.slice(0, 2).map((t) => (
                              <Badge key={t.tag_id} variant="secondary" className="text-[10px] px-1 py-0">
                                {t.name}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={market.enabled ? 'default' : 'secondary'} className="text-xs">
                        {market.enabled ? 'Tradable' : 'Disabled'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{getSpread(market)}</TableCell>
                    <TableCell className="text-sm">{getLiquidity(market)}</TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isAdding}
                        onClick={() => onAddMarket(market)}
                      >
                        {isAdding ? '...' : 'Add market'}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" disabled={pagination.offset === 0} onClick={onPagePrev}>
          <ChevronLeft className="h-4 w-4 mr-1" />
          Anterior
        </Button>
        <span className="text-sm text-muted-foreground">
          {pagination.offset + 1}–{pagination.offset + markets.length}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!pagination.hasMore}
          onClick={onPageNext}
        >
          Siguiente
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  );
}
