'use client';

import { useState } from 'react';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { useComponentDataLoader } from '@/hooks/useComponentDataLoader';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useStackApp } from '@stackframe/stack';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SidePanel } from '@/components/ui/side-panel';
import { Badge } from '@/components/ui/badge';
import { Copy, Check } from 'lucide-react';
import { MetricChip } from '@/components/ui/metric-chip';
import { Panel } from '@/components/ui/panel';

interface Market {
  market_id: string;
  polymarket_id: string;
  name: string;
  category: string | null;
  enabled: boolean;
  series_id: string | null;
  series_name: string | null;
  tags: Array<{ tag_id: string; name: string }>;
  events_count: number;
  polymarket_payload?: {
    clobTokenIds?: { YES?: string; NO?: string } | string[];
    outcomes?: Array<{ outcome: string; token_id?: string }>;
  };
}

interface MarketsData {
  markets: Market[];
}

export default function MarketsPage() {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
  const [copiedTokenId, setCopiedTokenId] = useState<string | null>(null);

  const { data, renderSkeleton } = useComponentDataLoader<MarketsData & { orderbookMetrics?: Record<string, any> }>({
    fetchFn: async () => {
      if (!user || !stackApp) {
        throw new Error('User not authenticated');
      }
      const api = initApiClient(createTokenGetter(user, stackApp));
      const [markets, orderbookMetrics] = await Promise.all([
        api.get<Market[]>('/markets').catch(() => []),
        api.get<Record<string, any>>('/markets/orderbook-metrics').catch(() => ({}))
      ]);
      return { markets, orderbookMetrics };
    },
    dependencies: [user, stackApp],
    refreshInterval: 30000,
    enabled: !!user && !!stackApp,
    showSkeleton: true,
    skeletonComponent: () => (
      <div className="space-y-2">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="h-9 bg-muted animate-pulse rounded" />
        ))}
      </div>
    ),
  });

  const handleCopyTokenId = async (tokenId: string) => {
    await navigator.clipboard.writeText(tokenId);
    setCopiedTokenId(tokenId);
    setTimeout(() => setCopiedTokenId(null), 2000);
  };

  const getClobTokenIds = (market: Market): { YES?: string; NO?: string } => {
    const payload = market.polymarket_payload;
    if (!payload?.clobTokenIds) return {};
    
    if (typeof payload.clobTokenIds === 'string') {
      try {
        const parsed = JSON.parse(payload.clobTokenIds);
        if (typeof parsed === 'object' && parsed !== null) {
          return parsed;
        }
      } catch {
        return {};
      }
    }
    
    if (Array.isArray(payload.clobTokenIds)) {
      return {
        YES: payload.clobTokenIds[0],
        NO: payload.clobTokenIds[1],
      };
    }
    
    if (typeof payload.clobTokenIds === 'object') {
      return payload.clobTokenIds as { YES?: string; NO?: string };
    }
    
    return {};
  };

  const filteredMarkets = data?.markets?.filter((market) => {
    if (searchTerm && !market.name.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    if (categoryFilter !== 'all' && market.category !== categoryFilter) {
      return false;
    }
    return true;
  }) || [];

  const categories = Array.from(new Set(data?.markets?.map(m => m.category).filter(Boolean) || []));

  return (
    <Layout>
      <div className="space-y-2">
        {/* Topbar compacto con filtros */}
        <div className="flex items-center gap-2 flex-wrap">
          <Input
            placeholder="Buscar markets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Categoría" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las categorías</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat} value={cat || ''}>
                  {cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {!isConnected && (
            <Badge variant="outline" className="text-[11px]">
              Demo Mode
            </Badge>
          )}
        </div>

        {/* Tabla densa */}
        {renderSkeleton}
        {data && (
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Market</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>YES Token</TableHead>
                  <TableHead>NO Token</TableHead>
                  <TableHead>Spread</TableHead>
                  <TableHead>Liquidity</TableHead>
                  <TableHead>Impact</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredMarkets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                      No se encontraron markets
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMarkets.map((market) => {
                    const tokenIds = getClobTokenIds(market);
                    // Obtener métricas de orderbook si están disponibles
                    const yesTokenId = tokenIds.YES;
                    const orderbookData = yesTokenId && data?.orderbookMetrics?.[yesTokenId];
                    
                    // Formatear métricas
                    const spreadBps = orderbookData?.spread_bps;
                    const spreadDisplay = spreadBps != null ? `${Math.round(spreadBps)} bps` : 'N/A';
                    const spreadColor = spreadBps != null 
                      ? (spreadBps < 50 ? 'green' : spreadBps < 150 ? 'yellow' : 'red')
                      : 'gray';
                    
                    const depthUsdc = orderbookData?.depth_usdc_at_50bps || 0;
                    const depthDisplay = depthUsdc > 0 
                      ? `$${(depthUsdc / 1000).toFixed(1)}k` 
                      : 'N/A';
                    
                    const impactBps = orderbookData?.impact_bps_for_usdc_1000 || 0;
                    const impactDisplay = impactBps > 0 
                      ? `${Math.round(impactBps)} bps` 
                      : 'N/A';
                    
                    return (
                      <TableRow
                        key={market.market_id}
                        className="cursor-pointer"
                        onClick={() => setSelectedMarket(market)}
                      >
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <span className="font-medium text-[13px]">{market.name}</span>
                            {market.tags && market.tags.length > 0 && (
                              <div className="flex gap-1 flex-wrap">
                                {market.tags.slice(0, 2).map((tag) => (
                                  <Badge key={tag.tag_id} variant="secondary" className="text-[10px] px-1.5 py-0">
                                    {tag.name}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={market.enabled ? 'default' : 'secondary'} className="text-[11px]">
                            {market.enabled ? 'Tradable' : 'Disabled'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {tokenIds.YES ? (
                            <div className="flex items-center gap-1">
                              <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded truncate max-w-[120px]">
                                {tokenIds.YES.slice(0, 8)}...
                              </code>
                              <Button
                                variant="ghost"
                                size="compact-sm"
                                className="h-6 w-6 p-0"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCopyTokenId(tokenIds.YES!);
                                }}
                              >
                                {copiedTokenId === tokenIds.YES ? (
                                  <Check className="h-3 w-3" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </Button>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-[11px]">N/A</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {tokenIds.NO ? (
                            <div className="flex items-center gap-1">
                              <code className="text-[11px] font-mono bg-muted px-1.5 py-0.5 rounded truncate max-w-[120px]">
                                {tokenIds.NO.slice(0, 8)}...
                              </code>
                              <Button
                                variant="ghost"
                                size="compact-sm"
                                className="h-6 w-6 p-0"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCopyTokenId(tokenIds.NO!);
                                }}
                              >
                                {copiedTokenId === tokenIds.NO ? (
                                  <Check className="h-3 w-3" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </Button>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-[11px]">N/A</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <MetricChip
                            label=""
                            value={spreadDisplay}
                            color={spreadColor}
                            tooltip="Diferencia entre mejor bid y ask. Spread bajo = más liquidez."
                          />
                        </TableCell>
                        <TableCell>
                          <MetricChip
                            label=""
                            value={depthDisplay}
                            tooltip="Liquidez disponible a 50bps del mejor precio"
                          />
                        </TableCell>
                        <TableCell>
                          <MetricChip
                            label=""
                            value={impactDisplay}
                            tooltip="Impacto en precio al ejecutar $1000"
                          />
                        </TableCell>
                        <TableCell>
                          <Button
                            size="compact-sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              // TODO: Add to universe
                            }}
                          >
                            Add to Universe
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Side Panel con detalles */}
        <SidePanel
          open={!!selectedMarket}
          onClose={() => setSelectedMarket(null)}
          title={selectedMarket?.name}
        >
          {selectedMarket && (
            <div className="space-y-3">
              <Panel>
                <h4 className="text-sm font-semibold mb-2">Outcomes</h4>
                <div className="space-y-2">
                  {selectedMarket.polymarket_payload?.outcomes?.map((outcome, idx) => (
                    <div key={idx} className="flex items-center justify-between text-[13px]">
                      <span>{outcome.outcome}</span>
                      {outcome.token_id && (
                        <code className="text-[11px] font-mono bg-muted px-2 py-1 rounded">
                          {outcome.token_id.slice(0, 16)}...
                        </code>
                      )}
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel>
                <h4 className="text-sm font-semibold mb-2">Token IDs</h4>
                <div className="space-y-2">
                  {Object.entries(getClobTokenIds(selectedMarket)).map(([outcome, tokenId]) => (
                    <div key={outcome} className="flex items-center justify-between gap-2">
                      <span className="text-[13px]">{outcome}:</span>
                      <div className="flex items-center gap-1 flex-1">
                        <code className="text-[11px] font-mono bg-muted px-2 py-1 rounded flex-1 truncate">
                          {tokenId}
                        </code>
                        <Button
                          size="compact-sm"
                          variant="ghost"
                          onClick={() => handleCopyTokenId(tokenId)}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>
              <Button
                size="compact"
                className="w-full"
                onClick={() => {
                  // TODO: Add to universe
                  setSelectedMarket(null);
                }}
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
