'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
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
import { toast } from '@/components/ui/sonner';
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
  ChevronDown
} from 'lucide-react';

// Strategy templates
const STRATEGY_TEMPLATES = {
  Liquidity: {
    id: 'liquidity_near_end',
    name: 'Liquidity Near Resolution',
    description: 'Provee liquidez cuando un evento ya terminó pero aún no ha sido resuelto por Polymarket.',
    executionVenue: 'polymarket',
    hideVenues: ['pinnacle', 'bet365'],
  },
};

interface Wallet {
  id: string;
  name: string;
  address: string;
  balance: number;
  allowance: number;
  status: 'ok' | 'limited' | 'error';
}

interface Checker {
  id: string;
  name: string;
  type: 'crypto' | 'sports' | 'custom';
  enabled: boolean;
  config: Record<string, any>;
}

export default function NewStrategyByTypePage() {
  const params = useParams();
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyType = params.type as string;

  const template = STRATEGY_TEMPLATES[strategyType as keyof typeof STRATEGY_TEMPLATES];

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [checkers, setCheckers] = useState<Checker[]>([]);

  // 0. Template Selection (already done via URL)
  // 1. Identity
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // 2. Execution Account
  const [selectedWallet, setSelectedWallet] = useState<string>('');

  // 3. Capital & Risk
  const [maxCapital, setMaxCapital] = useState(5000);
  const [maxExposurePerEvent, setMaxExposurePerEvent] = useState(2000);
  const [maxPositions, setMaxPositions] = useState(5);
  const [orderSizeType, setOrderSizeType] = useState<'fixed' | 'range'>('fixed');
  const [orderSizeFixed, setOrderSizeFixed] = useState(1000);
  const [orderSizeMin, setOrderSizeMin] = useState(500);
  const [orderSizeMax, setOrderSizeMax] = useState(2000);

  // 4. Entry Conditions
  const [priceRangeMin, setPriceRangeMin] = useState(0.95);
  const [priceRangeMax, setPriceRangeMax] = useState(0.98);
  const [maxTimeToResolution, setMaxTimeToResolution] = useState(30);
  const [minLiquidity, setMinLiquidity] = useState(2000);

  // 5. Markets & Events
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>([]);
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [autoAttach, setAutoAttach] = useState(false);

  // 6. Checkers
  const [enabledCheckers, setEnabledCheckers] = useState<string[]>([]);

  // 7. Execution Behavior
  const [executeImmediately, setExecuteImmediately] = useState(true);
  const [staggerOrders, setStaggerOrders] = useState(false);
  const [maxRetries, setMaxRetries] = useState(3);
  const [cooldownSeconds, setCooldownSeconds] = useState(5);

  // 8. Advanced
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [allowManualEdit, setAllowManualEdit] = useState(false);

  useEffect(() => {
    if (!template) {
      router.push('/strategies/new');
      return;
    }

    if (!user) {
      setLoading(false);
      return;
    }

    const loadData = async () => {
      try {
        setLoading(true);
        const api = initApiClient(createTokenGetter(user, stackApp));
        
        // Load wallets
        const walletsData = await api.get<Wallet[]>('/wallets?venue=polymarket').catch(() => []);
        setWallets(walletsData ?? []);
        if (walletsData && walletsData.length > 0) {
          setSelectedWallet(walletsData[0].id);
        }

        // Load checkers
        const checkersData = await api.get<Checker[]>('/checkers').catch(() => []);
        setCheckers(checkersData ?? []);

        // Set default name
        setName(`${template.name} - ${new Date().toLocaleDateString()}`);
      } catch (err) {
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user, stackApp, template, router]);

  const handleSave = async () => {
    if (!user || !name.trim() || !selectedWallet) {
      return;
    }

    setSaving(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));

      const strategyData = {
        name,
        description,
        tags,
        template_id: template.id,
        execution_account: {
          wallet_id: selectedWallet,
        },
        capital_risk: {
          max_capital: maxCapital,
          max_exposure_per_event: maxExposurePerEvent,
          max_positions: maxPositions,
          order_size: orderSizeType === 'fixed' 
            ? { type: 'fixed', value: orderSizeFixed }
            : { type: 'range', min: orderSizeMin, max: orderSizeMax },
        },
        entry_conditions: {
          price_range: { min: priceRangeMin, max: priceRangeMax },
          max_time_to_resolution_minutes: maxTimeToResolution,
          min_liquidity_usdc: minLiquidity,
        },
        markets_events: {
          categories: selectedCategories,
          markets: selectedMarkets,
          events: selectedEvents,
          auto_attach: autoAttach,
        },
        checkers: enabledCheckers.map(id => ({
          checker_id: id,
          enabled: true,
        })),
        execution_behavior: {
          execute_immediately: executeImmediately,
          stagger_orders: staggerOrders,
          max_retries: maxRetries,
          cooldown_seconds: cooldownSeconds,
        },
      };

      const newStrategy = await api.post<{ id: string }>('/api/strategies', strategyData);
      if (newStrategy?.id) router.push(`/strategies/${newStrategy.id}/live`);
    } catch (err) {
      console.error('Error saving strategy:', err);
      toast.error(err instanceof Error ? err.message : 'Error al guardar estrategia');
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

  const selectedWalletData = wallets.find(w => w.id === selectedWallet);

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-6xl mx-auto pb-12">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-foreground">Nueva Estrategia: {template.name}</h1>
            <p className="text-sm text-muted-foreground mt-1">{template.description}</p>
          </div>
          <Button onClick={handleSave} disabled={saving || !name.trim() || !selectedWallet}>
            {saving ? 'Guardando...' : 'Crear Estrategia'}
          </Button>
        </div>

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
                placeholder="Ej: Liquidity Provider - Q1 2024"
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
                placeholder="liquidity, near-resolution, low-risk"
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        {/* 2. Execution Account */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Wallet className="h-5 w-5" />
              2. Cuenta / Wallet de Ejecución *
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {wallets.length === 0 ? (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  No hay wallets configuradas. <a href="/settings/wallets" className="underline">Configurar wallets</a>
                </AlertDescription>
              </Alert>
            ) : (
              <>
                <div>
                  <Label htmlFor="wallet">Seleccionar Wallet</Label>
                  <Select value={selectedWallet} onValueChange={setSelectedWallet}>
                    <SelectTrigger id="wallet" className="mt-1">
                      <SelectValue placeholder="Selecciona una wallet" />
                    </SelectTrigger>
                    <SelectContent>
                      {wallets.map((wallet) => (
                        <SelectItem key={wallet.id} value={wallet.id}>
                          {wallet.name} ({wallet.address.slice(0, 8)}...)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {selectedWalletData && (
                  <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                    <div>
                      <div className="text-xs text-muted-foreground">Balance</div>
                      <div className="text-sm font-semibold">${selectedWalletData.balance.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Allowance</div>
                      <div className="text-sm font-semibold">${selectedWalletData.allowance.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Estado</div>
                      <Badge 
                        variant={
                          selectedWalletData.status === 'ok' ? 'success' :
                          selectedWalletData.status === 'limited' ? 'warning' : 'error'
                        }
                      >
                        {selectedWalletData.status === 'ok' ? 'OK' :
                         selectedWalletData.status === 'limited' ? 'Limited' : 'Error'}
                      </Badge>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* 3. Capital & Risk */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              3. Capital y Riesgo
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
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
                <Label htmlFor="maxExposurePerEvent">Exposición máxima por evento (USDC)</Label>
                <Input
                  id="maxExposurePerEvent"
                  type="number"
                  value={maxExposurePerEvent}
                  onChange={(e) => setMaxExposurePerEvent(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="maxPositions">Número máximo de posiciones simultáneas</Label>
              <Input
                id="maxPositions"
                type="number"
                value={maxPositions}
                onChange={(e) => setMaxPositions(Number(e.target.value))}
                className="mt-1"
              />
            </div>
            <Separator />
            <div>
              <Label>Tamaño de orden</Label>
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
                    checked={orderSizeType === 'range'}
                    onChange={() => setOrderSizeType('range')}
                  />
                  <span className="text-sm">Rango (min / max)</span>
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
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <Input
                    type="number"
                    value={orderSizeMin}
                    onChange={(e) => setOrderSizeMin(Number(e.target.value))}
                    placeholder="Mínimo"
                  />
                  <Input
                    type="number"
                    value={orderSizeMax}
                    onChange={(e) => setOrderSizeMax(Number(e.target.value))}
                    placeholder="Máximo"
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 4. Entry Conditions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="h-5 w-5" />
              4. Condiciones de Entrada
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Rango de precios aceptable</Label>
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={priceRangeMin}
                    onChange={(e) => setPriceRangeMin(Number(e.target.value))}
                    placeholder="Mínimo (ej: 0.95)"
                  />
                </div>
                <div>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={priceRangeMax}
                    onChange={(e) => setPriceRangeMax(Number(e.target.value))}
                    placeholder="Máximo (ej: 0.98)"
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Comprar solo entre {priceRangeMin} y {priceRangeMax}
              </p>
            </div>
            <div>
              <Label htmlFor="maxTimeToResolution">Tiempo máximo antes de resolución (minutos)</Label>
              <Input
                id="maxTimeToResolution"
                type="number"
                value={maxTimeToResolution}
                onChange={(e) => setMaxTimeToResolution(Number(e.target.value))}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Solo si faltan menos de {maxTimeToResolution} minutos para resolución
              </p>
            </div>
            <div>
              <Label htmlFor="minLiquidity">Liquidez mínima en el book (USDC)</Label>
              <Input
                id="minLiquidity"
                type="number"
                value={minLiquidity}
                onChange={(e) => setMinLiquidity(Number(e.target.value))}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Para evitar books muertos
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 5. Markets & Events */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Globe className="h-5 w-5" />
              5. Mercados y Eventos
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Categorías</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {['Sports', 'Crypto', 'Politics', 'Entertainment'].map((cat) => (
                  <label key={cat} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedCategories.includes(cat)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedCategories([...selectedCategories, cat]);
                        } else {
                          setSelectedCategories(selectedCategories.filter(c => c !== cat));
                        }
                      }}
                    />
                    <span className="text-sm">{cat}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <Label>Auto-attach eventos elegibles</Label>
              <label className="flex items-center gap-2 mt-2">
                <input
                  type="checkbox"
                  checked={autoAttach}
                  onChange={(e) => setAutoAttach(e.target.checked)}
                />
                <span className="text-sm">Activar automáticamente eventos que cumplan las condiciones</span>
              </label>
            </div>
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                La selección manual de mercados y eventos específicos estará disponible después de crear la estrategia.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* 6. Checkers */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5" />
              6. Confirmación Externa (Checkers)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {checkers.length === 0 ? (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  No hay checkers configurados. <a href="/settings/checkers" className="underline">Configurar checkers</a>
                </AlertDescription>
              </Alert>
            ) : (
              <div className="space-y-3">
                {checkers.map((checker) => (
                  <div key={checker.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium">{checker.name}</div>
                      <div className="text-xs text-muted-foreground">
                        Tipo: {checker.type === 'crypto' ? 'Crypto' : checker.type === 'sports' ? 'Sports' : 'Custom'}
                      </div>
                    </div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={enabledCheckers.includes(checker.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEnabledCheckers([...enabledCheckers, checker.id]);
                          } else {
                            setEnabledCheckers(enabledCheckers.filter(id => id !== checker.id));
                          }
                        }}
                      />
                      <span className="text-sm">Activar</span>
                    </label>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 7. Execution Behavior */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-5 w-5" />
              7. Comportamiento de Ejecución
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={executeImmediately}
                onChange={(e) => setExecuteImmediately(e.target.checked)}
              />
              <span className="text-sm">Ejecutar inmediatamente al confirmar</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={staggerOrders}
                onChange={(e) => setStaggerOrders(e.target.checked)}
              />
              <span className="text-sm">Escalonar órdenes</span>
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="maxRetries">Reintentos si falla</Label>
                <Input
                  id="maxRetries"
                  type="number"
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="cooldownSeconds">Cooldown entre órdenes (segundos)</Label>
                <Input
                  id="cooldownSeconds"
                  type="number"
                  value={cooldownSeconds}
                  onChange={(e) => setCooldownSeconds(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 8. Advanced */}
        <Accordion type="single" collapsible>
          <AccordionItem value="advanced">
            <AccordionTrigger>
              <div className="flex items-center gap-2">
                <ChevronDown className="h-4 w-4" />
                <span className="font-semibold">8. Advanced (Opcional)</span>
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
          <Button onClick={handleSave} disabled={saving || !name.trim() || !selectedWallet}>
            {saving ? 'Guardando...' : 'Crear Estrategia'}
          </Button>
        </div>
      </div>
    </Layout>
  );
}

