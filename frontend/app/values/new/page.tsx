'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { 
  Target, 
  Globe, 
  Zap, 
  TrendingUp, 
  Clock, 
  Shield, 
  Settings,
  AlertCircle,
  CheckCircle2,
  Info,
  Filter,
  Eye,
  Link2,
  Activity
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { toast } from '@/components/ui/sonner';

interface SourceConfig {
  id: string;
  name: string;
  enabled: boolean;
  weight?: number;
  maxLatency?: number;
  maxDataAge?: number;
}

interface MarketScope {
  sports?: {
    sports: string[];
    leagues: string[];
  };
  crypto?: {
    assets: string[];
    eventTypes: string[];
  };
  politics?: boolean;
}

export default function NewValueConfigPage() {
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [valueType, setValueType] = useState<'surebet' | 'near-resolution' | 'liquidity-gap' | 'custom'>('surebet');
  const [customType, setCustomType] = useState('');

  // Market Scope
  const [marketTypes, setMarketTypes] = useState<{
    sports: boolean;
    crypto: boolean;
    politics: boolean;
  }>({
    sports: true,
    crypto: true,
    politics: false,
  });
  const [sportsList, setSportsList] = useState<string[]>([]);
  const [leaguesList, setLeaguesList] = useState<string[]>([]);
  const [cryptoAssets, setCryptoAssets] = useState<string[]>([]);
  const [cryptoEventTypes, setCryptoEventTypes] = useState<string[]>([]);

  // Sources
  const [sources, setSources] = useState<SourceConfig[]>([]);

  // Edge Definition
  const [minEdgePercent, setMinEdgePercent] = useState(2.5);
  const [minNetEdgePercent, setMinNetEdgePercent] = useState(2.0);
  const [minAbsoluteEdge, setMinAbsoluteEdge] = useState(10);
  const [dynamicThreshold, setDynamicThreshold] = useState(false);

  // Confidence & Validation
  const [minSources, setMinSources] = useState(2);
  const [minPersistenceSeconds, setMinPersistenceSeconds] = useState(5);
  const [requireTemporalConsistency, setRequireTemporalConsistency] = useState(true);
  const [killOnContradiction, setKillOnContradiction] = useState(true);

  // Timing
  const [maxSignalAge, setMaxSignalAge] = useState(30);
  const [pollingFrequency, setPollingFrequency] = useState(2);
  const [invalidationTimeout, setInvalidationTimeout] = useState(10);
  const [reappearanceCooldown, setReappearanceCooldown] = useState(60);

  // Executability Filters
  const [minLiquidity, setMinLiquidity] = useState(1000);
  const [minBookDepth, setMinBookDepth] = useState(500);
  const [maxSpread, setMaxSpread] = useState(0.02);
  const [minOrderSize, setMinOrderSize] = useState(10);
  const [hideNonExecutable, setHideNonExecutable] = useState(true);

  // Risk-Aware Filters
  const [hideVolatile, setHideVolatile] = useState(true);
  const [hideDelayedResolution, setHideDelayedResolution] = useState(true);
  const [eventBlacklist, setEventBlacklist] = useState<string[]>([]);
  const [requireVenueHealth, setRequireVenueHealth] = useState(true);

  // Strategy Compatibility
  const [compatibleStrategies, setCompatibleStrategies] = useState<{
    surebet: boolean;
    liquidity: boolean;
    nearResolution: boolean;
    custom: boolean;
  }>({
    surebet: true,
    liquidity: false,
    nearResolution: false,
    custom: false,
  });

  // Output Behavior
  const [showTopN, setShowTopN] = useState(true);
  const [topNCount, setTopNCount] = useState(10);
  const [sortBy, setSortBy] = useState<'edge' | 'confidence' | 'duration'>('edge');
  const [highlightDecay, setHighlightDecay] = useState(true);
  const [autoHideLowConfidence, setAutoHideLowConfidence] = useState(true);

  // Advanced
  const [jsonPreview, setJsonPreview] = useState('');

  useEffect(() => {
    if (!user) return;

    const loadData = async () => {
      try {
        setLoading(true);
        const api = initApiClient(createTokenGetter(user, stackApp));
        
        // Load available sources
        // TODO: Replace with actual API call
        setSources([
          { id: 'polymarket', name: 'Polymarket', enabled: true, weight: 1.0, maxLatency: 1000, maxDataAge: 5 },
          { id: 'pinnacle', name: 'Pinnacle', enabled: true, weight: 0.8, maxLatency: 2000, maxDataAge: 10 },
          { id: 'binance', name: 'Binance', enabled: false, weight: 0.6, maxLatency: 500, maxDataAge: 2 },
          { id: 'espn', name: 'ESPN', enabled: false, weight: 0.7, maxLatency: 5000, maxDataAge: 30 },
        ]);
      } catch (err) {
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user, stackApp]);

  // Generate JSON preview
  useEffect(() => {
    const config = {
      name,
      description,
      valueType: valueType === 'custom' ? customType : valueType,
      marketScope: {
        sports: marketTypes.sports ? { sports: sportsList, leagues: leaguesList } : undefined,
        crypto: marketTypes.crypto ? { assets: cryptoAssets, eventTypes: cryptoEventTypes } : undefined,
        politics: marketTypes.politics,
      },
      sources: sources.filter(s => s.enabled),
      edgeCriteria: {
        minEdgePercent,
        minNetEdgePercent,
        minAbsoluteEdge,
        dynamicThreshold,
      },
      validation: {
        minSources,
        minPersistenceSeconds,
        requireTemporalConsistency,
        killOnContradiction,
      },
      timing: {
        maxSignalAge,
        pollingFrequency,
        invalidationTimeout,
        reappearanceCooldown,
      },
      executability: {
        minLiquidity,
        minBookDepth,
        maxSpread,
        minOrderSize,
        hideNonExecutable,
      },
      riskAware: {
        hideVolatile,
        hideDelayedResolution,
        eventBlacklist,
        requireVenueHealth,
      },
      strategyCompatibility: compatibleStrategies,
      output: {
        showTopN,
        topNCount,
        sortBy,
        highlightDecay,
        autoHideLowConfidence,
      },
    };
    setJsonPreview(JSON.stringify(config, null, 2));
  }, [
    name, description, valueType, customType, marketTypes, sportsList, leaguesList,
    cryptoAssets, cryptoEventTypes, sources, minEdgePercent, minNetEdgePercent,
    minAbsoluteEdge, dynamicThreshold, minSources, minPersistenceSeconds,
    requireTemporalConsistency, killOnContradiction, maxSignalAge, pollingFrequency,
    invalidationTimeout, reappearanceCooldown, minLiquidity, minBookDepth, maxSpread,
    minOrderSize, hideNonExecutable, hideVolatile, hideDelayedResolution, eventBlacklist,
    requireVenueHealth, compatibleStrategies, showTopN, topNCount, sortBy,
    highlightDecay, autoHideLowConfidence,
  ]);

  const handleSave = async () => {
    if (!user || !name.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }

    try {
      setSaving(true);
      const api = initApiClient(createTokenGetter(user, stackApp));
      
      const config = {
        name,
        description,
        valueType: valueType === 'custom' ? customType : valueType,
        marketScope: {
          sports: marketTypes.sports ? { sports: sportsList, leagues: leaguesList } : undefined,
          crypto: marketTypes.crypto ? { assets: cryptoAssets, eventTypes: cryptoEventTypes } : undefined,
          politics: marketTypes.politics,
        },
        sources: sources.filter(s => s.enabled),
        edgeCriteria: {
          minEdgePercent,
          minNetEdgePercent,
          minAbsoluteEdge,
          dynamicThreshold,
        },
        validation: {
          minSources,
          minPersistenceSeconds,
          requireTemporalConsistency,
          killOnContradiction,
        },
        timing: {
          maxSignalAge,
          pollingFrequency,
          invalidationTimeout,
          reappearanceCooldown,
        },
        executability: {
          minLiquidity,
          minBookDepth,
          maxSpread,
          minOrderSize,
          hideNonExecutable,
        },
        riskAware: {
          hideVolatile,
          hideDelayedResolution,
          eventBlacklist,
          requireVenueHealth,
        },
        strategyCompatibility: compatibleStrategies,
        output: {
          showTopN,
          topNCount,
          sortBy,
          highlightDecay,
          autoHideLowConfidence,
        },
      };

      // TODO: Replace with actual API endpoint
      // await api.post('/values/config', config);
      
      toast.success('Configuración de Value guardada exitosamente');
      router.push('/strategies');
    } catch (err) {
      toast.error('Error al guardar: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setSaving(false);
    }
  };

  const toggleSource = (sourceId: string) => {
    setSources(prev => prev.map(s => 
      s.id === sourceId ? { ...s, enabled: !s.enabled } : s
    ));
  };

  const updateSource = (sourceId: string, updates: Partial<SourceConfig>) => {
    setSources(prev => prev.map(s => 
      s.id === sourceId ? { ...s, ...updates } : s
    ));
  };

  if (loading) {
    return (
      <Layout>
        <LoadingSpinner text="Cargando configuración..." />
      </Layout>
    );
  }

  if (!user) return null;

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-5xl mx-auto pb-12">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">Nueva Estrategia: Values Configuration</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Define qué se considera &quot;value&quot; y bajo qué condiciones una señal es válida, visible y accionable
          </p>
        </div>

        {/* 1. Scope & Identity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Scope & Identity
            </CardTitle>
            <CardDescription>
              Define el perfil de value y su tipo
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nombre del Value Profile *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej: Surebet High Confidence"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Descripción (opcional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descripción del perfil de value..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="valueType">Tipo de Value</Label>
              <Select value={valueType} onValueChange={(v: any) => setValueType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="surebet">Surebet</SelectItem>
                  <SelectItem value="near-resolution">Near-resolution</SelectItem>
                  <SelectItem value="liquidity-gap">Liquidity Gap</SelectItem>
                  <SelectItem value="custom">Custom (avanzado)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {valueType === 'custom' && (
              <div className="space-y-2">
                <Label htmlFor="customType">Tipo Custom</Label>
                <Input
                  id="customType"
                  value={customType}
                  onChange={(e) => setCustomType(e.target.value)}
                  placeholder="Nombre del tipo custom"
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* 2. Market Scope */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Market Scope
            </CardTitle>
            <CardDescription>
              Dónde buscar value
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <Label>Tipos de Mercado</Label>
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="market-sports"
                    checked={marketTypes.sports}
                    onCheckedChange={(checked) => 
                      setMarketTypes(prev => ({ ...prev, sports: checked as boolean }))
                    }
                  />
                  <Label htmlFor="market-sports" className="font-normal cursor-pointer">
                    Sports
                  </Label>
                </div>
                {marketTypes.sports && (
                  <div className="ml-6 space-y-2">
                    <div className="space-y-2">
                      <Label className="text-xs">Deportes permitidos (separados por coma)</Label>
                      <Input
                        value={sportsList.join(', ')}
                        onChange={(e) => setSportsList(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                        placeholder="Ej: Football, Basketball, Soccer"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">Ligas permitidas (separadas por coma)</Label>
                      <Input
                        value={leaguesList.join(', ')}
                        onChange={(e) => setLeaguesList(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                        placeholder="Ej: NFL, NBA, Premier League"
                      />
                    </div>
                  </div>
                )}
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="market-crypto"
                    checked={marketTypes.crypto}
                    onCheckedChange={(checked) => 
                      setMarketTypes(prev => ({ ...prev, crypto: checked as boolean }))
                    }
                  />
                  <Label htmlFor="market-crypto" className="font-normal cursor-pointer">
                    Crypto
                  </Label>
                </div>
                {marketTypes.crypto && (
                  <div className="ml-6 space-y-2">
                    <div className="space-y-2">
                      <Label className="text-xs">Assets (separados por coma)</Label>
                      <Input
                        value={cryptoAssets.join(', ')}
                        onChange={(e) => setCryptoAssets(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                        placeholder="Ej: BTC, ETH, SOL"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs">Tipos de eventos (separados por coma)</Label>
                      <Input
                        value={cryptoEventTypes.join(', ')}
                        onChange={(e) => setCryptoEventTypes(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                        placeholder="Ej: Price, Volume, Market Cap"
                      />
                    </div>
                  </div>
                )}
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="market-politics"
                    checked={marketTypes.politics}
                    onCheckedChange={(checked) => 
                      setMarketTypes(prev => ({ ...prev, politics: checked as boolean }))
                    }
                  />
                  <Label htmlFor="market-politics" className="font-normal cursor-pointer">
                    Politics
                  </Label>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 3. Source Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              Signal Sources
            </CardTitle>
            <CardDescription>
              Selecciona y configura las fuentes de datos para las señales
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {sources.map((source) => (
                <Card key={source.id} className="border">
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <Switch
                          checked={source.enabled}
                          onCheckedChange={() => toggleSource(source.id)}
                        />
                        <div>
                          <Label className="font-medium">{source.name}</Label>
                          <div className="text-xs text-muted-foreground mt-1">
                            {source.enabled ? (
                              <Badge variant="outline" className="bg-green-50 text-green-700">
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                Enabled
                              </Badge>
                            ) : (
                              <Badge variant="outline">Disabled</Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    {source.enabled && (
                      <div className="mt-4 space-y-3 ml-11">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-2">
                            <Label className="text-xs">Weight (0-1)</Label>
                            <Input
                              type="number"
                              step="0.1"
                              min="0"
                              max="1"
                              value={source.weight || 0}
                              onChange={(e) => updateSource(source.id, { weight: parseFloat(e.target.value) })}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Max Latency (ms)</Label>
                            <Input
                              type="number"
                              value={source.maxLatency || 0}
                              onChange={(e) => updateSource(source.id, { maxLatency: parseInt(e.target.value) })}
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs">Max Data Age (seconds)</Label>
                          <Input
                            type="number"
                            value={source.maxDataAge || 0}
                            onChange={(e) => updateSource(source.id, { maxDataAge: parseInt(e.target.value) })}
                          />
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 4. Edge Definition */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Edge Criteria
            </CardTitle>
            <CardDescription>
              Define qué se considera edge suficiente
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="minEdgePercent">
                  Edge Mínimo (%)
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 inline ml-1 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Edge bruto mínimo antes de fees</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </Label>
                <Input
                  id="minEdgePercent"
                  type="number"
                  step="0.1"
                  value={minEdgePercent}
                  onChange={(e) => setMinEdgePercent(parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="minNetEdgePercent">
                  Edge Neto Mínimo (%)
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 inline ml-1 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Edge después de todos los fees</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </Label>
                <Input
                  id="minNetEdgePercent"
                  type="number"
                  step="0.1"
                  value={minNetEdgePercent}
                  onChange={(e) => setMinNetEdgePercent(parseFloat(e.target.value))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="minAbsoluteEdge">
                Edge Absoluto Mínimo ($)
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Info className="h-3 w-3 inline ml-1 text-muted-foreground" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Profit mínimo en dólares, independiente del porcentaje</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </Label>
              <Input
                id="minAbsoluteEdge"
                type="number"
                step="0.1"
                value={minAbsoluteEdge}
                onChange={(e) => setMinAbsoluteEdge(parseFloat(e.target.value))}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="dynamicThreshold"
                checked={dynamicThreshold}
                onCheckedChange={setDynamicThreshold}
              />
              <Label htmlFor="dynamicThreshold" className="font-normal cursor-pointer">
                Threshold dinámico (ajuste automático según condiciones de mercado)
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* 5. Confidence & Validation Rules */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Signal Validation
            </CardTitle>
            <CardDescription>
              Reglas de confianza y validación de señales
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="minSources">
                  Nº Mínimo de Fuentes Confirmando
                </Label>
                <Input
                  id="minSources"
                  type="number"
                  min="1"
                  value={minSources}
                  onChange={(e) => setMinSources(parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="minPersistenceSeconds">
                  Tiempo Mínimo de Persistencia (segundos)
                </Label>
                <Input
                  id="minPersistenceSeconds"
                  type="number"
                  min="1"
                  value={minPersistenceSeconds}
                  onChange={(e) => setMinPersistenceSeconds(parseInt(e.target.value))}
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="requireTemporalConsistency"
                checked={requireTemporalConsistency}
                onCheckedChange={setRequireTemporalConsistency}
              />
              <Label htmlFor="requireTemporalConsistency" className="font-normal cursor-pointer">
                Requerir consistencia temporal
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="killOnContradiction"
                checked={killOnContradiction}
                onCheckedChange={setKillOnContradiction}
              />
              <Label htmlFor="killOnContradiction" className="font-normal cursor-pointer">
                Eliminar señal si hay contradicciones
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* 6. Timing & Freshness */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Timing Constraints
            </CardTitle>
            <CardDescription>
              Control de frescura y validez temporal de las señales
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="maxSignalAge">Max Age of Signal (segundos)</Label>
                <Input
                  id="maxSignalAge"
                  type="number"
                  value={maxSignalAge}
                  onChange={(e) => setMaxSignalAge(parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pollingFrequency">Polling Frequency (segundos)</Label>
                <Input
                  id="pollingFrequency"
                  type="number"
                  value={pollingFrequency}
                  onChange={(e) => setPollingFrequency(parseInt(e.target.value))}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="invalidationTimeout">Invalidation Timeout (segundos)</Label>
                <Input
                  id="invalidationTimeout"
                  type="number"
                  value={invalidationTimeout}
                  onChange={(e) => setInvalidationTimeout(parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reappearanceCooldown">Reappearance Cooldown (segundos)</Label>
                <Input
                  id="reappearanceCooldown"
                  type="number"
                  value={reappearanceCooldown}
                  onChange={(e) => setReappearanceCooldown(parseInt(e.target.value))}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 7. Liquidity & Executability Filters */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Executability Filters
            </CardTitle>
            <CardDescription>
              Filtros de liquidez y ejecutabilidad
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="minLiquidity">Liquidez Mínima Requerida ($)</Label>
                <Input
                  id="minLiquidity"
                  type="number"
                  value={minLiquidity}
                  onChange={(e) => setMinLiquidity(parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="minBookDepth">Book Depth Mínima ($)</Label>
                <Input
                  id="minBookDepth"
                  type="number"
                  value={minBookDepth}
                  onChange={(e) => setMinBookDepth(parseFloat(e.target.value))}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="maxSpread">Max Spread Permitido (0-1)</Label>
                <Input
                  id="maxSpread"
                  type="number"
                  step="0.001"
                  min="0"
                  max="1"
                  value={maxSpread}
                  onChange={(e) => setMaxSpread(parseFloat(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="minOrderSize">Min Order Size Viable ($)</Label>
                <Input
                  id="minOrderSize"
                  type="number"
                  value={minOrderSize}
                  onChange={(e) => setMinOrderSize(parseFloat(e.target.value))}
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="hideNonExecutable"
                checked={hideNonExecutable}
                onCheckedChange={setHideNonExecutable}
              />
              <Label htmlFor="hideNonExecutable" className="font-normal cursor-pointer">
                Ocultar values no ejecutables (en lugar de mostrarlos como &quot;non-executable&quot;)
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* 8. Risk-Aware Filters */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Risk Awareness
            </CardTitle>
            <CardDescription>
              Filtros de riesgo sin asignar riesgo a la estrategia
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Switch
                  id="hideVolatile"
                  checked={hideVolatile}
                  onCheckedChange={setHideVolatile}
                />
                <Label htmlFor="hideVolatile" className="font-normal cursor-pointer">
                  Ocultar values si el mercado es muy volátil
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="hideDelayedResolution"
                  checked={hideDelayedResolution}
                  onCheckedChange={setHideDelayedResolution}
                />
                <Label htmlFor="hideDelayedResolution" className="font-normal cursor-pointer">
                  Ocultar si hay retrasos históricos en resolución
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="requireVenueHealth"
                  checked={requireVenueHealth}
                  onCheckedChange={setRequireVenueHealth}
                />
                <Label htmlFor="requireVenueHealth" className="font-normal cursor-pointer">
                  Requerir salud del venue
                </Label>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="eventBlacklist">Event Blacklist (IDs separados por coma)</Label>
              <Input
                id="eventBlacklist"
                value={eventBlacklist.join(', ')}
                onChange={(e) => setEventBlacklist(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                placeholder="Ej: event-123, event-456"
              />
            </div>
          </CardContent>
        </Card>

        {/* 9. Strategy Compatibility Rules */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Strategy Matching
            </CardTitle>
            <CardDescription>
              Define qué tipos de estrategia pueden consumir este value
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="compat-surebet"
                checked={compatibleStrategies.surebet}
                onCheckedChange={(checked) => 
                  setCompatibleStrategies(prev => ({ ...prev, surebet: checked as boolean }))
                }
              />
              <Label htmlFor="compat-surebet" className="font-normal cursor-pointer">
                Surebet strategies
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="compat-liquidity"
                checked={compatibleStrategies.liquidity}
                onCheckedChange={(checked) => 
                  setCompatibleStrategies(prev => ({ ...prev, liquidity: checked as boolean }))
                }
              />
              <Label htmlFor="compat-liquidity" className="font-normal cursor-pointer">
                Liquidity strategies
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="compat-near-resolution"
                checked={compatibleStrategies.nearResolution}
                onCheckedChange={(checked) => 
                  setCompatibleStrategies(prev => ({ ...prev, nearResolution: checked as boolean }))
                }
              />
              <Label htmlFor="compat-near-resolution" className="font-normal cursor-pointer">
                Near-resolution strategies
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="compat-custom"
                checked={compatibleStrategies.custom}
                onCheckedChange={(checked) => 
                  setCompatibleStrategies(prev => ({ ...prev, custom: checked as boolean }))
                }
              />
              <Label htmlFor="compat-custom" className="font-normal cursor-pointer">
                Custom strategies
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* 10. Output Behavior */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Display & Surfacing
            </CardTitle>
            <CardDescription>
              Cómo se muestran los values en el Live Control
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="showTopN"
                checked={showTopN}
                onCheckedChange={setShowTopN}
              />
              <Label htmlFor="showTopN" className="font-normal cursor-pointer">
                Mostrar solo top N values
              </Label>
            </div>
            {showTopN && (
              <div className="ml-6 space-y-2">
                <Label htmlFor="topNCount">Número de values a mostrar</Label>
                <Input
                  id="topNCount"
                  type="number"
                  min="1"
                  value={topNCount}
                  onChange={(e) => setTopNCount(parseInt(e.target.value))}
                />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="sortBy">Ordenar por</Label>
              <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="edge">Edge</SelectItem>
                  <SelectItem value="confidence">Confidence</SelectItem>
                  <SelectItem value="duration">Duration</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="highlightDecay"
                checked={highlightDecay}
                onCheckedChange={setHighlightDecay}
              />
              <Label htmlFor="highlightDecay" className="font-normal cursor-pointer">
                Highlight decay (resaltar cuando el edge está decayendo)
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="autoHideLowConfidence"
                checked={autoHideLowConfidence}
                onCheckedChange={setAutoHideLowConfidence}
              />
              <Label htmlFor="autoHideLowConfidence" className="font-normal cursor-pointer">
                Auto-hide low confidence values
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* 11. Advanced */}
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="advanced">
            <AccordionTrigger>
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Advanced (Power Users)
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>JSON Preview (Read-only)</Label>
                      <Textarea
                        value={jsonPreview}
                        readOnly
                        className="font-mono text-xs"
                        rows={20}
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => {
                        try {
                          JSON.parse(jsonPreview);
                          toast.success('JSON válido');
                        } catch {
                          toast.error('JSON inválido');
                        }
                      }}>
                        Validate JSON
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={() => router.back()}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? 'Guardando...' : 'Guardar Configuración'}
          </Button>
        </div>
      </div>
    </Layout>
  );
}

