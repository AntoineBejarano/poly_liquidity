'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { 
  AlertCircle, 
  CheckCircle2, 
  Wallet, 
  DollarSign, 
  Target, 
  Globe, 
  Shield, 
  Settings,
  ChevronDown,
  Zap,
  Clock,
  TrendingUp,
  Link2,
  AlertTriangle,
  Info
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface Wallet {
  id: string;
  name: string;
  address: string;
  balance: number;
  allowance: number;
  status: 'ok' | 'limited' | 'error';
}

interface VenueConnection {
  id: string;
  name: string;
  type: 'pinnacle' | 'bet365' | 'custom';
  status: 'connected' | 'disconnected' | 'error';
  latency?: number;
  lastUpdate?: string;
}

interface MarketMatch {
  polymarketEvent: string;
  referenceEvent: string;
  confidence: 'high' | 'medium' | 'low';
  profitEstimate: number;
}

export default function SurebetStrategyPage() {
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [polymarketWallets, setPolymarketWallets] = useState<Wallet[]>([]);
  const [venueConnections, setVenueConnections] = useState<VenueConnection[]>([]);
  const [marketMatches, setMarketMatches] = useState<MarketMatch[]>([]);

  // 1. Identity
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // 2. Venue A - Polymarket
  const [venueAWallet, setVenueAWallet] = useState<string>('');
  const [venueACategories, setVenueACategories] = useState<string[]>([]);
  const [venueAMarkets, setVenueAMarkets] = useState<string[]>([]);
  const [venueAAutoDiscovery, setVenueAAutoDiscovery] = useState(true);
  const [venueAExecutionType, setVenueAExecutionType] = useState<'buy' | 'sell' | 'both'>('both');

  // 3. Venue B - Reference Venue
  const [venueBType, setVenueBType] = useState<'pinnacle' | 'bet365' | 'custom'>('pinnacle');
  const [venueBConnection, setVenueBConnection] = useState<string>('');
  const [venueBSports, setVenueBSports] = useState<string[]>([]);
  const [venueBMarkets, setVenueBMarkets] = useState<string[]>([]);
  const [venueBMode, setVenueBMode] = useState<'reference_only' | 'execute_both'>('reference_only');

  // 4. Market Matching
  const [matchingMode, setMatchingMode] = useState<'auto' | 'manual'>('auto');
  const [selectedMatches, setSelectedMatches] = useState<string[]>([]);

  // 5. Arbitrage Conditions
  const [minProfitPercent, setMinProfitPercent] = useState(2.0);
  const [minProfitAbsolute, setMinProfitAbsolute] = useState(10);
  const [minImpliedProbability, setMinImpliedProbability] = useState(0.5);
  const [edgeAfterFees, setEdgeAfterFees] = useState(1.5);
  const [slippageBuffer, setSlippageBuffer] = useState(0.5);

  // 6. Timing & Latency
  const [pollingFrequency, setPollingFrequency] = useState(5);
  const [maxLatency, setMaxLatency] = useState(2000);
  const [maxOddsAge, setMaxOddsAge] = useState(10);
  const [killSwitchStale, setKillSwitchStale] = useState(true);

  // 7. Position Sizing & Capital
  const [maxCapital, setMaxCapital] = useState(10000);
  const [orderSizeType, setOrderSizeType] = useState<'fixed' | 'percent'>('percent');
  const [orderSizeFixed, setOrderSizeFixed] = useState(1000);
  const [orderSizePercent, setOrderSizePercent] = useState(5);
  const [maxPerEvent, setMaxPerEvent] = useState(5000);
  const [maxSimultaneous, setMaxSimultaneous] = useState(3);

  // 8. Execution Coordination
  const [executionOrder, setExecutionOrder] = useState<'polymarket_first' | 'reference_first' | 'atomic'>('polymarket_first');
  const [abortOnFailure, setAbortOnFailure] = useState(true);
  const [maxRetries, setMaxRetries] = useState(2);
  const [handlePartialFill, setHandlePartialFill] = useState(true);

  // 9. Risk Controls
  const [maxNetExposure, setMaxNetExposure] = useState(20000);
  const [stopAfterFailures, setStopAfterFailures] = useState(5);
  const [cooldownAfterError, setCooldownAfterError] = useState(60);
  const [dailyLossLimit, setDailyLossLimit] = useState(1000);
  const [disableOnAnomaly, setDisableOnAnomaly] = useState(true);

  // 10. Fees & Profit Preview
  const [polymarketFee, setPolymarketFee] = useState(0.02);
  const [referenceFee, setReferenceFee] = useState(0.05);
  const [estimatedNetProfit, setEstimatedNetProfit] = useState(0);

  // 11. Advanced
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [allowManualEdit, setAllowManualEdit] = useState(false);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    const loadData = async () => {
      try {
        setLoading(true);
        const api = initApiClient(createTokenGetter(user, stackApp));
        
        // Load Polymarket wallets
        const walletsData = await api.get<Wallet[]>('/wallets?venue=polymarket').catch(() => []);
        setPolymarketWallets(walletsData);
        if (walletsData.length > 0) {
          setVenueAWallet(walletsData[0].id);
        }

        // Load venue connections
        const connectionsData = await api.get<VenueConnection[]>('/venue-connections').catch(() => []);
        setVenueConnections(connectionsData);
        if (connectionsData.length > 0) {
          const pinnacleConn = connectionsData.find(c => c.type === 'pinnacle');
          if (pinnacleConn) {
            setVenueBConnection(pinnacleConn.id);
          }
        }

        // Set default name
        setName(`Surebet Strategy - ${new Date().toLocaleDateString()}`);
      } catch (err) {
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user, stackApp]);

  // Calculate estimated net profit
  useEffect(() => {
    const grossProfit = minProfitPercent;
    const totalFees = polymarketFee + referenceFee;
    const netProfit = grossProfit - totalFees;
    setEstimatedNetProfit(Math.max(0, netProfit));
  }, [minProfitPercent, polymarketFee, referenceFee]);

  const handleSave = async () => {
    if (!user || !name.trim() || !venueAWallet || !venueBConnection) {
      alert('Por favor completa todos los campos obligatorios');
      return;
    }

    setSaving(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));

      const strategyData = {
        name,
        description,
        tags,
        template_id: 'surebet_polymarket_pinnacle',
        venue_a: {
          venue: 'polymarket',
          wallet_id: venueAWallet,
          categories: venueACategories,
          markets: venueAMarkets,
          auto_discovery: venueAAutoDiscovery,
          execution_type: venueAExecutionType,
        },
        venue_b: {
          venue: venueBType,
          connection_id: venueBConnection,
          sports: venueBSports,
          markets: venueBMarkets,
          mode: venueBMode,
        },
        market_matching: {
          mode: matchingMode,
          selected_matches: selectedMatches,
        },
        arbitrage_conditions: {
          min_profit_percent: minProfitPercent,
          min_profit_absolute: minProfitAbsolute,
          min_implied_probability: minImpliedProbability,
          edge_after_fees: edgeAfterFees,
          slippage_buffer: slippageBuffer,
        },
        timing_latency: {
          polling_frequency_seconds: pollingFrequency,
          max_latency_ms: maxLatency,
          max_odds_age_seconds: maxOddsAge,
          kill_switch_stale: killSwitchStale,
        },
        position_sizing: {
          max_capital: maxCapital,
          order_size_type: orderSizeType,
          order_size_fixed: orderSizeFixed,
          order_size_percent: orderSizePercent,
          max_per_event: maxPerEvent,
          max_simultaneous: maxSimultaneous,
        },
        execution_coordination: {
          execution_order: executionOrder,
          abort_on_failure: abortOnFailure,
          max_retries: maxRetries,
          handle_partial_fill: handlePartialFill,
        },
        risk_controls: {
          max_net_exposure: maxNetExposure,
          stop_after_failures: stopAfterFailures,
          cooldown_after_error_seconds: cooldownAfterError,
          daily_loss_limit: dailyLossLimit,
          disable_on_anomaly: disableOnAnomaly,
        },
        fees: {
          polymarket_fee: polymarketFee,
          reference_fee: referenceFee,
        },
      };

      const newStrategy = await api.post<{ id: string }>('/api/strategies', strategyData);
      router.push(`/strategies/${newStrategy.id}/live`);
    } catch (err) {
      console.error('Error saving strategy:', err);
      alert(err instanceof Error ? err.message : 'Error al guardar estrategia');
    } finally {
      setSaving(false);
    }
  };

  if (!user) return null;

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner fullScreen text="Cargando configuración..." />
      </Layout>
    );
  }

  const selectedVenueAWallet = polymarketWallets.find(w => w.id === venueAWallet);
  const selectedVenueBConn = venueConnections.find(c => c.id === venueBConnection);

  const isConfigurationValid = name.trim() && venueAWallet && venueBConnection;

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-6xl mx-auto pb-12">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-foreground">Nueva Estrategia: Surebet / Cross-Market Arbitrage</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Explota ineficiencias de precio entre dos venues con control estricto de riesgo y latencia
            </p>
          </div>
          <Button 
            onClick={handleSave} 
            disabled={saving || !isConfigurationValid}
            className="flex items-center gap-2"
          >
            {saving ? 'Guardando...' : 'Crear Estrategia'}
          </Button>
        </div>

        {!isConfigurationValid && (
          <Alert variant="warning">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Completa la configuración de Venue A y Venue B para activar la estrategia
            </AlertDescription>
          </Alert>
        )}

        {/* 1. Identity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">1. Identidad Básica</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="name">Nombre de la estrategia *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej: Surebet Polymarket-Pinnacle Q1 2024"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="description">Descripción (opcional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe el propósito de esta estrategia..."
                className="mt-1"
                rows={3}
              />
            </div>
            <div>
              <Label htmlFor="tags">Tags (opcional, separados por comas)</Label>
              <Input
                id="tags"
                value={tags.join(', ')}
                onChange={(e) => setTags(e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
                placeholder="surebet, arbitrage, cross-market"
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        {/* 2. Venue A - Polymarket */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="h-5 w-5" />
              2. Venue A – Polymarket (Execution)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="venueAWallet">Cuenta / Wallet *</Label>
              <Select value={venueAWallet} onValueChange={setVenueAWallet}>
                <SelectTrigger id="venueAWallet" className="mt-1">
                  <SelectValue placeholder="Selecciona una wallet Polymarket" />
                </SelectTrigger>
                <SelectContent>
                  {polymarketWallets.map((wallet) => (
                    <SelectItem key={wallet.id} value={wallet.id}>
                      {wallet.name} ({wallet.address.slice(0, 8)}...)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedVenueAWallet && (
                <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg mt-2">
                  <div>
                    <div className="text-xs text-muted-foreground">Balance</div>
                    <div className="text-sm font-semibold">${selectedVenueAWallet.balance.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Allowance</div>
                    <div className="text-sm font-semibold">${selectedVenueAWallet.allowance.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Estado</div>
                    <Badge 
                      variant={
                        selectedVenueAWallet.status === 'ok' ? 'success' :
                        selectedVenueAWallet.status === 'limited' ? 'warning' : 'error'
                      }
                    >
                      {selectedVenueAWallet.status === 'ok' ? 'OK' :
                       selectedVenueAWallet.status === 'limited' ? 'Limited' : 'Error'}
                    </Badge>
                  </div>
                </div>
              )}
            </div>

            <Separator />

            <div>
              <Label>Mercados</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {['Sports', 'Crypto', 'Politics', 'Entertainment'].map((cat) => (
                  <label key={cat} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={venueACategories.includes(cat)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setVenueACategories([...venueACategories, cat]);
                        } else {
                          setVenueACategories(venueACategories.filter(c => c !== cat));
                        }
                      }}
                    />
                    <span className="text-sm">{cat}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <Label>Auto-discovery de eventos elegibles</Label>
              <label className="flex items-center gap-2 mt-2">
                <input
                  type="checkbox"
                  checked={venueAAutoDiscovery}
                  onChange={(e) => setVenueAAutoDiscovery(e.target.checked)}
                />
                <span className="text-sm">Activar automáticamente eventos que cumplan las condiciones</span>
              </label>
            </div>

            <Separator />

            <div>
              <Label>Tipo de ejecución</Label>
              <div className="flex gap-4 mt-2">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={venueAExecutionType === 'buy'}
                    onChange={() => setVenueAExecutionType('buy')}
                  />
                  <span className="text-sm">Buy only</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={venueAExecutionType === 'sell'}
                    onChange={() => setVenueAExecutionType('sell')}
                  />
                  <span className="text-sm">Sell only</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={venueAExecutionType === 'both'}
                    onChange={() => setVenueAExecutionType('both')}
                  />
                  <span className="text-sm">Buy + Sell</span>
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 3. Venue B - Reference Venue */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              3. Venue B – Reference Venue
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="venueBType">Selección de venue *</Label>
              <Select value={venueBType} onValueChange={(v) => setVenueBType(v as any)}>
                <SelectTrigger id="venueBType" className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pinnacle">Pinnacle</SelectItem>
                  <SelectItem value="bet365" disabled>Bet365 (Próximamente)</SelectItem>
                  <SelectItem value="custom" disabled>Exchange X (Próximamente)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {venueBType === 'pinnacle' && (
              <>
                <div>
                  <Label htmlFor="venueBConnection">Conexión Pinnacle *</Label>
                  <Select value={venueBConnection} onValueChange={setVenueBConnection}>
                    <SelectTrigger id="venueBConnection" className="mt-1">
                      <SelectValue placeholder="Selecciona una conexión" />
                    </SelectTrigger>
                    <SelectContent>
                      {venueConnections
                        .filter(c => c.type === 'pinnacle')
                        .map((conn) => (
                          <SelectItem key={conn.id} value={conn.id}>
                            {conn.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>

                {selectedVenueBConn && (
                  <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                    <div>
                      <div className="text-xs text-muted-foreground">Estado</div>
                      <Badge 
                        variant={
                          selectedVenueBConn.status === 'connected' ? 'success' :
                          selectedVenueBConn.status === 'disconnected' ? 'warning' : 'error'
                        }
                      >
                        {selectedVenueBConn.status === 'connected' ? 'Conectado' :
                         selectedVenueBConn.status === 'disconnected' ? 'Desconectado' : 'Error'}
                      </Badge>
                    </div>
                    {selectedVenueBConn.latency && (
                      <div>
                        <div className="text-xs text-muted-foreground">Latencia media</div>
                        <div className="text-sm font-semibold">{selectedVenueBConn.latency}ms</div>
                      </div>
                    )}
                    {selectedVenueBConn.lastUpdate && (
                      <div>
                        <div className="text-xs text-muted-foreground">Última actualización</div>
                        <div className="text-sm font-semibold">{selectedVenueBConn.lastUpdate}</div>
                      </div>
                    )}
                  </div>
                )}

                <div>
                  <Label>Deportes permitidos</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {['Soccer', 'Basketball', 'Tennis', 'Baseball', 'Hockey'].map((sport) => (
                      <label key={sport} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={venueBSports.includes(sport)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setVenueBSports([...venueBSports, sport]);
                            } else {
                              setVenueBSports(venueBSports.filter(s => s !== sport));
                            }
                          }}
                        />
                        <span className="text-sm">{sport}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <Label>Modo</Label>
                  <div className="flex gap-4 mt-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={venueBMode === 'reference_only'}
                        onChange={() => setVenueBMode('reference_only')}
                      />
                      <span className="text-sm">Reference-only (default)</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={venueBMode === 'execute_both'}
                        onChange={() => setVenueBMode('execute_both')}
                        disabled
                      />
                      <span className="text-sm text-muted-foreground">Execute both sides (futuro)</span>
                    </label>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* 4. Market Matching */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="h-5 w-5" />
              4. Market & Event Matching
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Modo de matching</Label>
              <div className="flex gap-4 mt-2">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={matchingMode === 'auto'}
                    onChange={() => setMatchingMode('auto')}
                  />
                  <span className="text-sm">Auto-matching</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={matchingMode === 'manual'}
                    onChange={() => setMatchingMode('manual')}
                  />
                  <span className="text-sm">Manual override</span>
                </label>
              </div>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                El matching automático usa algoritmos de similitud para emparejar eventos entre venues.
                Revisa manualmente los matches de baja confianza antes de activar.
              </AlertDescription>
            </Alert>

            {marketMatches.length > 0 && (
              <div className="space-y-2">
                <Label>Matches detectados</Label>
                {marketMatches.map((match, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex-1">
                      <div className="text-sm font-medium">{match.polymarketEvent}</div>
                      <div className="text-xs text-muted-foreground">↔ {match.referenceEvent}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge 
                        variant={
                          match.confidence === 'high' ? 'success' :
                          match.confidence === 'medium' ? 'warning' : 'error'
                        }
                      >
                        {match.confidence === 'high' ? 'High' :
                         match.confidence === 'medium' ? 'Medium' : 'Low'}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        ${match.profitEstimate.toFixed(2)} profit
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 5. Arbitrage Conditions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              5. Condiciones de Arbitraje
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Label htmlFor="minProfitPercent" className="flex items-center gap-1">
                        Profit mínimo (%)
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </Label>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Porcentaje mínimo de profit bruto antes de fees</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <Input
                  id="minProfitPercent"
                  type="number"
                  step="0.1"
                  value={minProfitPercent}
                  onChange={(e) => setMinProfitPercent(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Label htmlFor="minProfitAbsolute" className="flex items-center gap-1">
                        Profit mínimo absoluto ($)
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </Label>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Profit mínimo en dólares independiente del porcentaje</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <Input
                  id="minProfitAbsolute"
                  type="number"
                  value={minProfitAbsolute}
                  onChange={(e) => setMinProfitAbsolute(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edgeAfterFees">Edge después de fees (%)</Label>
                <Input
                  id="edgeAfterFees"
                  type="number"
                  step="0.1"
                  value={edgeAfterFees}
                  onChange={(e) => setEdgeAfterFees(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="slippageBuffer">Buffer de slippage (%)</Label>
                <Input
                  id="slippageBuffer"
                  type="number"
                  step="0.1"
                  value={slippageBuffer}
                  onChange={(e) => setSlippageBuffer(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="minImpliedProbability">Probabilidad implícita mínima</Label>
              <Input
                id="minImpliedProbability"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={minImpliedProbability}
                onChange={(e) => setMinImpliedProbability(Number(e.target.value))}
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        {/* 6. Timing & Latency */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5" />
              6. Timing & Latency Control
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="pollingFrequency">Frecuencia de polling (segundos)</Label>
                <Input
                  id="pollingFrequency"
                  type="number"
                  value={pollingFrequency}
                  onChange={(e) => setPollingFrequency(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="maxLatency">Latencia máxima permitida (ms)</Label>
                <Input
                  id="maxLatency"
                  type="number"
                  value={maxLatency}
                  onChange={(e) => setMaxLatency(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="maxOddsAge">Máxima edad de odds (segundos)</Label>
                <Input
                  id="maxOddsAge"
                  type="number"
                  value={maxOddsAge}
                  onChange={(e) => setMaxOddsAge(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Kill-switch si odds están stale</Label>
                <label className="flex items-center gap-2 mt-2">
                  <input
                    type="checkbox"
                    checked={killSwitchStale}
                    onChange={(e) => setKillSwitchStale(e.target.checked)}
                  />
                  <span className="text-sm">Activar kill-switch automático</span>
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 7. Position Sizing & Capital */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              7. Position Sizing & Capital Allocation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="maxCapital">Capital máximo asignado (USDC)</Label>
              <Input
                id="maxCapital"
                type="number"
                value={maxCapital}
                onChange={(e) => setMaxCapital(Number(e.target.value))}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Tamaño por trade</Label>
              <div className="flex gap-4 mt-2">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={orderSizeType === 'fixed'}
                    onChange={() => setOrderSizeType('fixed')}
                  />
                  <span className="text-sm">Fijo</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={orderSizeType === 'percent'}
                    onChange={() => setOrderSizeType('percent')}
                  />
                  <span className="text-sm">% del capital</span>
                </label>
              </div>
              {orderSizeType === 'fixed' ? (
                <div className="mt-2">
                  <Input
                    type="number"
                    value={orderSizeFixed}
                    onChange={(e) => setOrderSizeFixed(Number(e.target.value))}
                    placeholder="Tamaño fijo en USDC"
                  />
                </div>
              ) : (
                <div className="mt-2">
                  <Input
                    type="number"
                    step="0.1"
                    value={orderSizePercent}
                    onChange={(e) => setOrderSizePercent(Number(e.target.value))}
                    placeholder="Porcentaje del capital"
                  />
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="maxPerEvent">Máximo por evento (USDC)</Label>
                <Input
                  id="maxPerEvent"
                  type="number"
                  value={maxPerEvent}
                  onChange={(e) => setMaxPerEvent(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="maxSimultaneous">Máximo trades simultáneos</Label>
                <Input
                  id="maxSimultaneous"
                  type="number"
                  value={maxSimultaneous}
                  onChange={(e) => setMaxSimultaneous(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 8. Execution Coordination */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="h-5 w-5" />
              8. Execution Coordination
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Orden de ejecución</Label>
              <div className="flex flex-col gap-2 mt-2">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={executionOrder === 'polymarket_first'}
                    onChange={() => setExecutionOrder('polymarket_first')}
                  />
                  <span className="text-sm">Execute Polymarket first</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={executionOrder === 'reference_first'}
                    onChange={() => setExecutionOrder('reference_first')}
                  />
                  <span className="text-sm">Execute reference first (si aplica)</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={executionOrder === 'atomic'}
                    onChange={() => setExecutionOrder('atomic')}
                  />
                  <span className="text-sm">Atomic attempt (best-effort)</span>
                </label>
              </div>
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="maxRetries">Reintentos</Label>
                <Input
                  id="maxRetries"
                  type="number"
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Protecciones</Label>
                <div className="space-y-2 mt-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={abortOnFailure}
                      onChange={(e) => setAbortOnFailure(e.target.checked)}
                    />
                    <span className="text-sm">Abort si falla uno de los lados</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={handlePartialFill}
                      onChange={(e) => setHandlePartialFill(e.target.checked)}
                    />
                    <span className="text-sm">Manejar partial fills</span>
                  </label>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 9. Risk Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5" />
              9. Risk Controls & Safeguards
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="maxNetExposure">Max exposure neta (USDC)</Label>
                <Input
                  id="maxNetExposure"
                  type="number"
                  value={maxNetExposure}
                  onChange={(e) => setMaxNetExposure(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="dailyLossLimit">Daily loss limit (USDC)</Label>
                <Input
                  id="dailyLossLimit"
                  type="number"
                  value={dailyLossLimit}
                  onChange={(e) => setDailyLossLimit(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="stopAfterFailures">Stop después de N fallos</Label>
                <Input
                  id="stopAfterFailures"
                  type="number"
                  value={stopAfterFailures}
                  onChange={(e) => setStopAfterFailures(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="cooldownAfterError">Cooldown tras error (segundos)</Label>
                <Input
                  id="cooldownAfterError"
                  type="number"
                  value={cooldownAfterError}
                  onChange={(e) => setCooldownAfterError(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
            <div>
              <Label>Disable strategy on anomaly detection</Label>
              <label className="flex items-center gap-2 mt-2">
                <input
                  type="checkbox"
                  checked={disableOnAnomaly}
                  onChange={(e) => setDisableOnAnomaly(e.target.checked)}
                />
                <span className="text-sm">Desactivar automáticamente si se detectan anomalías</span>
              </label>
            </div>
          </CardContent>
        </Card>

        {/* 10. Fees & Profit Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              10. Fees & Net Profit Preview
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="polymarketFee">Fees Polymarket (%)</Label>
                <Input
                  id="polymarketFee"
                  type="number"
                  step="0.01"
                  value={polymarketFee}
                  onChange={(e) => setPolymarketFee(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="referenceFee">Fees Pinnacle (%)</Label>
                <Input
                  id="referenceFee"
                  type="number"
                  step="0.01"
                  value={referenceFee}
                  onChange={(e) => setReferenceFee(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
            <Separator />
            <div className="p-4 bg-muted rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Profit bruto estimado:</span>
                <span className="text-sm font-semibold">{minProfitPercent.toFixed(2)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Total fees:</span>
                <span className="text-sm font-semibold">{(polymarketFee + referenceFee).toFixed(2)}%</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">Profit neto estimado:</span>
                <span className={`text-lg font-bold ${estimatedNetProfit > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {estimatedNetProfit.toFixed(2)}%
                </span>
              </div>
              <div className="text-xs text-muted-foreground mt-2">
                Break-even threshold: {(polymarketFee + referenceFee).toFixed(2)}%
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 11. Advanced */}
        <Accordion type="single" collapsible>
          <AccordionItem value="advanced">
            <AccordionTrigger>
              <div className="flex items-center gap-2">
                <ChevronDown className="h-4 w-4" />
                <span className="font-semibold">11. Advanced (Opcional)</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <Card>
                <CardContent className="pt-6 space-y-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={allowManualEdit}
                      onChange={(e) => setAllowManualEdit(e.target.checked)}
                    />
                    <span className="text-sm">Permitir edición manual del JSON</span>
                  </label>
                  {allowManualEdit && (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        La edición manual del JSON puede romper la estrategia. Úsalo solo si sabes lo que haces.
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Save Button */}
        <div className="flex justify-end gap-4 pt-4 border-t">
          <Button variant="outline" onClick={() => router.back()}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving || !isConfigurationValid}>
            {saving ? 'Guardando...' : 'Crear Estrategia'}
          </Button>
        </div>
      </div>
    </Layout>
  );
}

