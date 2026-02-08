'use client';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RefreshCw } from 'lucide-react';
import type { DiscoveryTag, DiscoveryView } from '@/lib/discovery/types';
import type { Strategy } from '@/types/strategy';

const TAG_FILTER_THRESHOLD = 8;

interface DiscoveryTopBarProps {
  searchTerm: string;
  onSearchChange: (v: string) => void;
  view: DiscoveryView;
  onViewChange: (v: DiscoveryView) => void;
  tagId: string;
  onTagChange: (v: string) => void;
  tags: DiscoveryTag[];
  tagFilterInput: string;
  onTagFilterInputChange: (v: string) => void;
  order: string;
  onOrderChange: (v: string) => void;
  closed: boolean;
  onClosedChange: (v: boolean) => void;
  strategies: Strategy[];
  selectedStrategyId: string;
  onStrategyChange: (v: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  lastFetchedAt: number | null;
  isDemo?: boolean;
}

export function DiscoveryTopBar({
  searchTerm,
  onSearchChange,
  view,
  onViewChange,
  tagId,
  onTagChange,
  tags,
  tagFilterInput,
  onTagFilterInputChange,
  order,
  onOrderChange,
  closed,
  onClosedChange,
  strategies,
  selectedStrategyId,
  onStrategyChange,
  onRefresh,
  isRefreshing,
  lastFetchedAt,
  isDemo = false,
}: DiscoveryTopBarProps) {
  const filteredTags =
    tagFilterInput.trim() === ''
      ? tags
      : tags.filter((t) =>
          (t.name || t.tag_id).toLowerCase().includes(tagFilterInput.trim().toLowerCase())
        );

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        placeholder="Buscar (~500ms debounce)..."
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        className="flex-1 min-w-[180px]"
      />
      <div className="flex rounded-md border border-input overflow-hidden">
        {(['markets', 'events', 'series'] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => onViewChange(v)}
            className={`px-3 py-2 text-sm font-medium transition-colors ${
              view === v
                ? 'bg-primary text-primary-foreground'
                : 'bg-background hover:bg-muted'
            }`}
          >
            {v === 'markets' ? 'Markets' : v === 'events' ? 'Events' : 'Series'}
          </button>
        ))}
      </div>
      <Select value={tagId || 'all'} onValueChange={(v) => onTagChange(v === 'all' ? '' : v)}>
        <SelectTrigger className="w-[160px]" onPointerDown={(e) => e.stopPropagation()}>
          <SelectValue placeholder="Tag" />
        </SelectTrigger>
        <SelectContent>
          {tags.length > TAG_FILTER_THRESHOLD && (
            <div className="p-2 border-b border-border">
              <Input
                placeholder="Buscar tag..."
                value={tagFilterInput}
                onChange={(e) => onTagFilterInputChange(e.target.value)}
                className="h-8 text-sm bg-background text-foreground"
                onPointerDown={(e) => e.stopPropagation()}
              />
            </div>
          )}
          <SelectItem value="all">Todos los tags</SelectItem>
          {filteredTags.map((t) => (
            <SelectItem key={t.tag_id} value={t.tag_id}>
              {t.name || t.tag_id}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={order} onValueChange={onOrderChange}>
        <SelectTrigger className="w-[140px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="createdAt">Recientes</SelectItem>
          <SelectItem value="volume">Volumen</SelectItem>
          <SelectItem value="liquidity">Liquidez</SelectItem>
          <SelectItem value="closed">Cerrados</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={closed ? 'closed' : 'active'}
        onValueChange={(v) => onClosedChange(v === 'closed')}
      >
        <SelectTrigger className="w-[120px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="active">Activos</SelectItem>
          <SelectItem value="closed">Cerrados</SelectItem>
        </SelectContent>
      </Select>
      {!isDemo && (
        <Select
          value={selectedStrategyId || '_none'}
          onValueChange={(v) => onStrategyChange(v === '_none' ? '' : v)}
        >
          <SelectTrigger className="w-[200px]" aria-label="Estrategia">
            <SelectValue placeholder="Estrategia (Add to)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="_none">— Ninguna —</SelectItem>
            {strategies.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {s.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {!isDemo && (
        <>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-label="Actualizar"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          {lastFetchedAt != null && (
            <span className="text-xs text-muted-foreground">
              Actualizado hace {Math.max(0, Math.floor((Date.now() - lastFetchedAt) / 1000))} s
            </span>
          )}
        </>
      )}
    </div>
  );
}
