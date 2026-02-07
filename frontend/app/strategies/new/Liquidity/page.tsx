'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { InlineForm } from '@/components/ui/inline-form';
import { Panel } from '@/components/ui/panel';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from '@/components/ui/sonner';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

// Mapeo UI → Backend
const FIELD_MAPPING: Record<string, string> = {
  "Book Freshness": "max_book_staleness_ms",
  "Max Spread": "max_spread_bps",
  "Min Liquidity": "min_depth_usdc_at_50bps",
  "Max Price Impact": "max_impact_bps",
  "Wait After Finish": "min_seconds_since_finished",
  "Max Time After Finish": "max_seconds_since_finished",
  "Order Size": "order_usdc",
  "Smart Sizing": "capacity_sizing_enabled",
  "Order Type": "order_mode",
  "Order Timeout": "ttl_ms",
  "Price Drift Limit": "drift_bps_limit",
  "Price Step": "tick_size",
  "Improve Price By": "improve_ticks",
};

export default function LiquidityStrategyPage() {
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();

  // Identity
  const [name, setName] = useState(`Liquidity Near Resolution - ${new Date().toLocaleDateString()}`);
  const [description, setDescription] = useState('');

  // Universe
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>([]);
  const [autoAttach, setAutoAttach] = useState(true);

  // Orderbook Constraints
  const [maxBookStalenessMs, setMaxBookStalenessMs] = useState(2000);
  const [maxSpreadBps, setMaxSpreadBps] = useState(200);
  const [minDepthUsdc, setMinDepthUsdc] = useState(2000);
  const [maxImpactBps, setMaxImpactBps] = useState(50);

  // Timing
  const [minSecondsSinceFinished, setMinSecondsSinceFinished] = useState(60);
  const [maxSecondsSinceFinished, setMaxSecondsSinceFinished] = useState(1800);

  // Sizing
  const [orderUsdc, setOrderUsdc] = useState(1000);
  const [capacitySizingEnabled, setCapacitySizingEnabled] = useState(true);

  // Execution
  const [orderMode, setOrderMode] = useState<'IOC' | 'POST_ONLY'>('IOC');
  const [ttlMs, setTtlMs] = useState(5000);
  const [driftBpsLimit, setDriftBpsLimit] = useState(20);
  const [tickSize, setTickSize] = useState(0.001);
  const [improveTicks, setImproveTicks] = useState(1);

  // Validaciones
  const warnings: string[] = [];
  if (orderMode === 'POST_ONLY' && improveTicks === 0) {
    warnings.push('Tu precio iguala el mejor bid. Podría no ejecutarse.');
  }
  if (maxImpactBps < 30) {
    warnings.push('Impacto máximo muy bajo. El tamaño de orden será pequeño.');
  }
  if (minDepthUsdc > 5000) {
    warnings.push('Liquidez mínima muy alta. Pocos mercados cumplirán este requisito.');
  }

  const handleSave = async () => {
    if (!user || !name.trim()) return;

    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      
      // Intentar cargar fuentes externas (opcional)
      let externalSourceId: string | undefined;
      try {
        const sources = await api.get<Array<{ id: string; name: string }>>('/external-data-sources?is_active=true');
        if (sources && sources.length > 0) {
          externalSourceId = sources[0].id;
        }
      } catch (e) {
        console.warn('No se pudieron cargar fuentes externas, continuando sin ellas');
      }
      
      // Primero compilar el template con la config
      // Mapear campos de UI a campos que espera el compilador
      const templateId = 'liquidity_near_end';
      const config: Record<string, any> = {
        // Campos que el compilador actual espera
        event_finished: true,
        external_confirmation_required: true,
        allow_ambiguity: false,
        price_min: 0.95, // TODO: Añadir estos campos al UI
        price_max: 0.98, // TODO: Añadir estos campos al UI
        max_size_per_event: orderUsdc,
        min_liquidity: minDepthUsdc,
        min_spread: maxSpreadBps / 100, // Convertir bps a porcentaje
        // Campos adicionales para futuro (el compilador los ignorará por ahora)
        max_book_staleness_ms: maxBookStalenessMs,
        max_spread_bps: maxSpreadBps,
        min_depth_usdc_at_50bps: minDepthUsdc,
        max_impact_bps: maxImpactBps,
        min_seconds_since_finished: minSecondsSinceFinished,
        max_seconds_since_finished: maxSecondsSinceFinished,
        capacity_sizing_enabled: capacitySizingEnabled,
        order_mode: orderMode,
        ttl_ms: ttlMs,
        drift_bps_limit: driftBpsLimit,
        tick_size: tickSize,
        improve_ticks: improveTicks,
      };
      
      // Añadir external_source_id solo si está disponible
      if (externalSourceId) {
        config.external_source_id = externalSourceId;
      }

      // Compilar template
      const compiled = await api.post<{
        decision_graph: any;
        support_graphs?: any[];
        execution_graph?: any;
      }>(`/strategy-templates/${templateId}/compile`, config);

      // Crear estrategia con el decision_graph compilado
      const strategyData = {
        name,
        description,
        decision_graph: compiled.decision_graph,
        support_graphs: compiled.support_graphs || [],
        execution_graph: compiled.execution_graph,
        tags: ['liquidity', 'near-resolution'],
        universe_config: {
          categories: selectedCategories,
          markets: selectedMarkets,
          tags: [],
          auto_attach: autoAttach,
          deny_list: [],
        },
      };

      const newStrategy = await api.post<{ id: string }>('/api/strategies', strategyData);
      router.push(`/strategies/${newStrategy.id}/live`);
    } catch (err) {
      console.error('Error saving strategy:', err);
      const errorMessage = err instanceof Error ? err.message : 'Error al guardar estrategia';
      toast.error(errorMessage);
    }
  };

  if (!user) return null;

  return (
    <Layout>
      <div className="flex gap-2 h-[calc(100vh-120px)]">
        {/* Universe (25%) */}
        <div className="w-[25%] border-r p-3 space-y-2 overflow-y-auto">
          <h3 className="text-sm font-semibold">Universe</h3>
          <div className="space-y-2">
            <div>
              <Label className="text-[13px]">Categories</Label>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {['Sports', 'Crypto', 'Politics', 'Entertainment'].map((cat) => (
                  <Badge
                    key={cat}
                    variant={selectedCategories.includes(cat) ? 'default' : 'outline'}
                    className="text-[11px] cursor-pointer"
                    onClick={() => {
                      if (selectedCategories.includes(cat)) {
                        setSelectedCategories(selectedCategories.filter(c => c !== cat));
                      } else {
                        setSelectedCategories([...selectedCategories, cat]);
                      }
                    }}
                  >
                    {cat}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-[13px]">Auto-attach</Label>
              <label className="flex items-center gap-2 mt-1">
                <input
                  type="checkbox"
                  checked={autoAttach}
                  onChange={(e) => setAutoAttach(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-[13px]">Auto-attach nuevos events</span>
              </label>
            </div>
          </div>
        </div>

        {/* Knobs (50%) */}
        <div className="flex-1 p-3 space-y-2 overflow-y-auto">
          <h3 className="text-sm font-semibold">Configuration</h3>
          <Accordion type="multiple" className="space-y-2" defaultValue={['orderbook', 'timing', 'sizing', 'execution']}>
            <AccordionItem value="orderbook" className="border rounded-lg">
              <AccordionTrigger className="px-3 py-2 text-sm">
                Orderbook Constraints
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3 space-y-2">
                <InlineForm
                  label="Book Freshness"
                  tooltip="Tiempo máximo sin actualizarse (ms). Si es muy alto, precios desactualizados."
                  input={
                    <Input
                      type="number"
                      value={maxBookStalenessMs}
                      onChange={(e) => setMaxBookStalenessMs(Number(e.target.value))}
                      placeholder="ms"
                    />
                  }
                />
                <InlineForm
                  label="Max Spread"
                  tooltip="Diferencia máxima entre bid y ask (bps). Spread alto = menos liquidez."
                  input={
                    <Input
                      type="number"
                      value={maxSpreadBps}
                      onChange={(e) => setMaxSpreadBps(Number(e.target.value))}
                      placeholder="bps"
                    />
                  }
                />
                <InlineForm
                  label="Min Liquidity"
                  tooltip="Liquidez mínima a 50bps del mejor precio (USDC)."
                  input={
                    <Input
                      type="number"
                      value={minDepthUsdc}
                      onChange={(e) => setMinDepthUsdc(Number(e.target.value))}
                      placeholder="USDC"
                    />
                  }
                />
                <InlineForm
                  label="Max Price Impact"
                  tooltip="Impacto máximo en precio al ejecutar (bps). Impacto alto = mueve el mercado."
                  input={
                    <Input
                      type="number"
                      value={maxImpactBps}
                      onChange={(e) => setMaxImpactBps(Number(e.target.value))}
                      placeholder="bps"
                    />
                  }
                />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="timing" className="border rounded-lg">
              <AccordionTrigger className="px-3 py-2 text-sm">
                Timing
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3 space-y-2">
                <InlineForm
                  label="Wait After Finish"
                  tooltip="Segundos mínimos a esperar después de que termine el evento. Evita falsos positivos."
                  input={
                    <Input
                      type="number"
                      value={minSecondsSinceFinished}
                      onChange={(e) => setMinSecondsSinceFinished(Number(e.target.value))}
                      placeholder="segundos"
                    />
                  }
                />
                <InlineForm
                  label="Max Time After Finish"
                  tooltip="Segundos máximos después de que termine el evento. Evita entrar cuando la liquidez ya se agotó."
                  input={
                    <Input
                      type="number"
                      value={maxSecondsSinceFinished}
                      onChange={(e) => setMaxSecondsSinceFinished(Number(e.target.value))}
                      placeholder="segundos"
                    />
                  }
                />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="sizing" className="border rounded-lg">
              <AccordionTrigger className="px-3 py-2 text-sm">
                Sizing
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3 space-y-2">
                <InlineForm
                  label="Order Size"
                  tooltip="Tamaño de orden en USDC (fijo o rango)."
                  input={
                    <Input
                      type="number"
                      value={orderUsdc}
                      onChange={(e) => setOrderUsdc(Number(e.target.value))}
                      placeholder="USDC"
                    />
                  }
                />
                <InlineForm
                  label="Smart Sizing"
                  tooltip="Ajusta automáticamente el tamaño según la liquidez disponible."
                  input={
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={capacitySizingEnabled}
                        onChange={(e) => setCapacitySizingEnabled(e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span className="text-[13px]">Enabled</span>
                    </label>
                  }
                />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="execution" className="border rounded-lg">
              <AccordionTrigger className="px-3 py-2 text-sm">
                Execution
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3 space-y-2">
                <InlineForm
                  label="Order Type"
                  tooltip="Market = ejecuta inmediatamente. Limit = espera a que alguien tome tu precio."
                  input={
                    <Select value={orderMode} onValueChange={(v) => setOrderMode(v as 'IOC' | 'POST_ONLY')}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="IOC">Market (IOC)</SelectItem>
                        <SelectItem value="POST_ONLY">Limit (POST_ONLY)</SelectItem>
                      </SelectContent>
                    </Select>
                  }
                />
                <InlineForm
                  label="Order Timeout"
                  tooltip="Tiempo máximo que la orden puede estar pendiente (ms)."
                  input={
                    <Input
                      type="number"
                      value={ttlMs}
                      onChange={(e) => setTtlMs(Number(e.target.value))}
                      placeholder="ms"
                    />
                  }
                />
                <InlineForm
                  label="Price Drift Limit"
                  tooltip="Cambio máximo permitido en precio desde que se creó el plan (bps)."
                  input={
                    <Input
                      type="number"
                      value={driftBpsLimit}
                      onChange={(e) => setDriftBpsLimit(Number(e.target.value))}
                      placeholder="bps"
                    />
                  }
                />
                <InlineForm
                  label="Price Step"
                  tooltip="Paso mínimo de precio permitido (ej: 0.001)."
                  input={
                    <Input
                      type="number"
                      step="0.0001"
                      value={tickSize}
                      onChange={(e) => setTickSize(Number(e.target.value))}
                      placeholder="0.001"
                    />
                  }
                />
                {orderMode === 'POST_ONLY' && (
                  <InlineForm
                    label="Improve Price By"
                    tooltip="Mejora el precio en X pasos respecto al mejor bid."
                    input={
                      <Input
                        type="number"
                        value={improveTicks}
                        onChange={(e) => setImproveTicks(Number(e.target.value))}
                        placeholder="ticks"
                      />
                    }
                  />
                )}
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          <div className="flex gap-2 pt-2">
            <Button variant="outline" size="compact" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button size="compact" onClick={handleSave} disabled={!name.trim()}>
              Create Strategy
            </Button>
          </div>
        </div>

        {/* Summary (25%) */}
        <div className="w-[25%] border-l p-3 space-y-2 overflow-y-auto">
          <h3 className="text-sm font-semibold">Summary</h3>
          <Panel>
            <div className="space-y-2">
              <div>
                <Label className="text-[11px] text-muted-foreground">Strategy Name</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Strategy name"
                  className="text-[13px]"
                />
              </div>
              {description && (
                <div>
                  <Label className="text-[11px] text-muted-foreground">Description</Label>
                  <p className="text-[13px]">{description}</p>
                </div>
              )}
            </div>
          </Panel>

          {warnings.length > 0 && (
            <Panel>
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Warnings</Label>
                {warnings.map((warning, idx) => (
                  <Alert key={idx} className="py-2">
                    <AlertCircle className="h-3 w-3" />
                    <AlertDescription className="text-[11px]">{warning}</AlertDescription>
                  </Alert>
                ))}
              </div>
            </Panel>
          )}

          <Panel>
            <div className="space-y-2">
              <Label className="text-[11px] text-muted-foreground">Configuration Summary</Label>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Order Size:</span>
                  <span>${orderUsdc.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Order Type:</span>
                  <span>{orderMode}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Spread:</span>
                  <span>{maxSpreadBps} bps</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Min Liquidity:</span>
                  <span>${minDepthUsdc.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Impact:</span>
                  <span>{maxImpactBps} bps</span>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </Layout>
  );
}

