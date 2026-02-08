'use client';

import { useParams } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { useState, useEffect, useCallback } from 'react';
import { Layout } from '@/components/Layout';
import { useDataMode } from '@/hooks/useDataMode';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { DiscoveryClient, getDomainBySlug, isValidDomainSlug } from '@/lib/discovery';
import { getTimeBucketMinutes, getEndDateMaxIso, isValidTimeBucket } from '@/lib/discovery/time-bucket';
import type { DiscoveryTradeableMarket } from '@/lib/discovery/types';
import type { Strategy } from '@/types/strategy';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SidePanel } from '@/components/ui/side-panel';
import { Badge } from '@/components/ui/badge';
import { MetricChip } from '@/components/ui/metric-chip';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import Link from 'next/link';
import { Copy, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { DiscoverySearchBar } from '@/components/markets/DiscoverySearchBar';
import { AddToUniverseConfirmDialog } from '@/components/markets/AddToUniverseConfirmDialog';
import { SortableTableHead } from '@/components/markets/SortableTableHead';
import { searchMarkets } from '@/lib/discovery';

const OVERFETCH_LIMIT = 100;
const UI_PAGE_SIZE = 50;
const TTR_FILTER_STRICT = true; // fail-closed: filtrar por TTR client-side

export default function DomainTimeBucketPage() {
  const params = useParams();
  const domainSlug = (params?.domain as string) ?? '';
  const timeBucketSlug = (params?.timeBucket as string) ?? '15M';
  const user = useUser();
  const stackApp = useStackApp();
  const { isDemo } = useDataMode();

  const [markets, setMarkets] = useState<DiscoveryTradeableMarket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [selectedMarket, setSelectedMarket] = useState<DiscoveryTradeableMarket | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('');
  const [addingToUniverse, setAddingToUniverse] = useState<string | null>(null);
  const [copiedTokenId, setCopiedTokenId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [marketToAdd, setMarketToAdd] = useState<DiscoveryTradeableMarket | null>(null);
  const [sortBy, setSortBy] = useState<string | null>('liquidity');
  const [sortAsc, setSortAsc] = useState(false);

  const domain = getDomainBySlug(domainSlug);
  const searched = searchQuery.trim()
    ? searchMarkets(markets, searchQuery)
    : markets;

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortAsc((a) => !a);
    } else {
      setSortBy(key);
      setSortAsc(key === 'question' ? true : false);
    }
  };

  const displayedMarkets = [...searched].sort((a, b) => {
    if (!sortBy) return 0;
    let cmp = 0;
    if (sortBy === 'question') {
      cmp = (a.question || '').localeCompare(b.question || '');
    } else if (sortBy === 'ttr') {
      const va = a.time_to_resolution_minutes ?? 999999;
      const vb = b.time_to_resolution_minutes ?? 999999;
      cmp = va - vb;
    } else if (sortBy === 'volume24hr') {
      cmp = (a.volume24hr ?? 0) - (b.volume24hr ?? 0);
    } else if (sortBy === 'liquidity') {
      cmp = (a.liquidity ?? 0) - (b.liquidity ?? 0);
    }
    return sortAsc ? cmp : -cmp;
  });
  const ttrMinutes = getTimeBucketMinutes(timeBucketSlug);
  const isValid = isValidDomainSlug(domainSlug) && domain?.supportsTimeBucket && isValidTimeBucket(timeBucketSlug);

  const fetchMarkets = useCallback(async (off: number, append: boolean) => {
    if (!domain?.gammaTagSlug || isDemo) return;
    setLoading(true);
    setError(null);
    try {
      const client = new DiscoveryClient(createTokenGetter(user ?? undefined, stackApp ?? undefined));
      const endDateMax = ttrMinutes != null ? getEndDateMaxIso(ttrMinutes) : undefined;
      const result = await client.fetchDiscovery({
        tag_slug: domain.gammaTagSlug,
        closed: false,
        limit: OVERFETCH_LIMIT,
        offset: off,
        end_date_max: endDateMax ?? undefined,
      });

      let filtered = result.markets;
      if (TTR_FILTER_STRICT && ttrMinutes != null) {
        filtered = result.markets.filter((m) => {
          const ttr = m.time_to_resolution_minutes;
          return ttr != null && ttr >= 0 && ttr <= ttrMinutes;
        });
      }

      setMarkets((prev) => (append ? [...prev, ...filtered] : filtered));
      setHasMore(result.markets.length >= OVERFETCH_LIMIT);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al cargar');
      setMarkets([]);
    } finally {
      setLoading(false);
    }
  }, [domain, ttrMinutes, isDemo, user, stackApp]);

  useEffect(() => {
    if (isValid && domain?.gammaTagSlug && !isDemo) {
      fetchMarkets(0, false);
    } else {
      setLoading(false);
      setMarkets([]);
    }
  }, [isValid, domain?.gammaTagSlug, isDemo, fetchMarkets]);

  useEffect(() => {
    if (!user || !stackApp || isDemo) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    api.get<Strategy[]>('/api/strategies', true).then((list) => {
      setStrategies(Array.isArray(list) ? list : []);
    }).catch(() => setStrategies([]));
  }, [user, stackApp, isDemo]);

  const handleAddToUniverse = async (market: DiscoveryTradeableMarket) => {
    if (!selectedStrategyId || !user || !stackApp || isDemo) {
      if (!selectedStrategyId) toast.error('Selecciona una estrategia');
      return;
    }
    setAddingToUniverse(market.polymarket_id);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/api/strategies/${selectedStrategyId}/universe/markets`, {
        market_id: market.polymarket_id,
      });
      toast.success('Añadido al universo');
      setSelectedMarket(null);
      setConfirmOpen(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Error al añadir');
    } finally {
      setAddingToUniverse(null);
    }
  };

  const handleRequestAddToUniverse = (market: DiscoveryTradeableMarket) => {
    if (!selectedStrategyId) {
      toast.error('Selecciona una estrategia');
      return;
    }
    setMarketToAdd(market);
    setConfirmOpen(true);
  };

  const handleConfirmAdd = async () => {
    if (!marketToAdd) return;
    await handleAddToUniverse(marketToAdd);
  };

  const handleCopyTokenId = async (tokenId: string) => {
    await navigator.clipboard.writeText(tokenId);
    setCopiedTokenId(tokenId);
    setTimeout(() => setCopiedTokenId(null), 2000);
  };

  const loadMore = () => {
    const nextOffset = offset + OVERFETCH_LIMIT;
    setOffset(nextOffset);
    fetchMarkets(nextOffset, true);
  };

  if (!isValid) {
    return (
      <Layout>
        <Alert variant="destructive">
          <AlertTitle>Ruta inválida</AlertTitle>
          <AlertDescription>
            Dominio o time bucket no válido. Usa /crypto/15M, /politics/1D, etc.
          </AlertDescription>
        </Alert>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-4 p-4">
        <Link href="/markets" className="text-sm text-muted-foreground hover:text-foreground">
          ← Markets
        </Link>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <h1 className="text-xl font-semibold">
              {domain?.domainSlug} / {timeBucketSlug}
            </h1>
            <div className="flex items-center gap-2">
              {!isDemo && (
                <Select value={selectedStrategyId || '_none'} onValueChange={(v) => setSelectedStrategyId(v === '_none' ? '' : v)}>
                  <SelectTrigger className="w-[200px]">
                    <SelectValue placeholder="Estrategia (Add to Universe)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">— Ninguna —</SelectItem>
                    {strategies.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Button variant="outline" size="sm" onClick={() => fetchMarkets(0, false)} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                Actualizar
              </Button>
            </div>
          </div>
          <DiscoverySearchBar value={searchQuery} onChange={setSearchQuery} placeholder="Buscar (btc, bitcoin...)" />
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading && markets.length === 0 ? (
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-10 bg-muted animate-pulse rounded" />
            ))}
          </div>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTableHead label="Market" sortKey="question" currentSortBy={sortBy} sortAsc={sortAsc} onSort={handleSort} />
                  <SortableTableHead label="TTR" sortKey="ttr" currentSortBy={sortBy} sortAsc={sortAsc} onSort={handleSort} />
                  <SortableTableHead label="Vol 24h" sortKey="volume24hr" currentSortBy={sortBy} sortAsc={sortAsc} onSort={handleSort} />
                  <SortableTableHead label="Liquidity" sortKey="liquidity" currentSortBy={sortBy} sortAsc={sortAsc} onSort={handleSort} />
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {markets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                      No hay mercados tradeables con estos filtros.
                    </TableCell>
                  </TableRow>
                ) : (
                  displayedMarkets.slice(0, UI_PAGE_SIZE).map((m) => (
                    <TableRow key={m.market_id} className="cursor-pointer" onClick={() => setSelectedMarket(m)}>
                      <TableCell>
                        <div>
                          <span className="font-medium text-sm">{m.question}</span>
                          {m.event_title && (
                            <p className="text-xs text-muted-foreground truncate max-w-md">{m.event_title}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {m.time_to_resolution_minutes != null ? (
                          <MetricChip value={`${Math.round(m.time_to_resolution_minutes)}m`} />
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell>
                        {m.volume24hr != null && m.volume24hr > 0 ? (
                          <span className="text-sm">${(m.volume24hr / 1000).toFixed(1)}k</span>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell>
                        {m.liquidity != null && m.liquidity > 0 ? (
                          <span className="text-sm">${(m.liquidity / 1000).toFixed(1)}k</span>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={!selectedStrategyId || !!addingToUniverse}
                          onClick={(e) => { e.stopPropagation(); handleRequestAddToUniverse(m); }}
                        >
                          Add to Universe
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        )}

        {hasMore && (
          <Button variant="outline" onClick={loadMore} disabled={loading}>
            Cargar más
          </Button>
        )}

        <AddToUniverseConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          market={marketToAdd}
          strategyName={strategies.find((s) => s.id === selectedStrategyId)?.name ?? ''}
          onConfirm={handleConfirmAdd}
          loading={!!addingToUniverse}
        />

        <SidePanel open={!!selectedMarket} onClose={() => setSelectedMarket(null)} title={selectedMarket?.question}>
          {selectedMarket && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">{selectedMarket.event_title}</p>
              {selectedMarket.clob_token_ids?.primary_yes && (
                <div className="flex items-center gap-2">
                  <code className="text-xs bg-muted px-2 py-1 rounded truncate flex-1">
                    {selectedMarket.clob_token_ids.primary_yes.slice(0, 20)}...
                  </code>
                  <Button size="sm" variant="ghost" onClick={() => handleCopyTokenId(selectedMarket.clob_token_ids!.primary_yes!)}>
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              )}
              <Button
                size="sm"
                className="w-full"
                disabled={!selectedStrategyId || !!addingToUniverse}
                onClick={() => handleRequestAddToUniverse(selectedMarket)}
              >
                Add to Strategy Universe
              </Button>
            </div>
          )}
        </SidePanel>
      </div>
    </Layout>
  );
}
