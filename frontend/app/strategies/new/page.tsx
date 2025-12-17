'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { initApiClient, createTokenGetter } from '@/lib/api';

type StrategyStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED';
type StrategyIntent = 'liquidity_near_resolution' | 'value_bets' | 'arbitrage' | 'custom';
type Participant = 'polymarket' | 'pinnacle' | 'bet365' | 'custom_api';

interface ExternalDataSource {
  id: string;
  name: string;
  connector_type: string;
  is_active: boolean;
}

export default function NewStrategyPage() {
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();

  const [strategyName, setStrategyName] = useState('Untitled Strategy');
  const [status, setStatus] = useState<StrategyStatus>('DRAFT');
  const [saving, setSaving] = useState(false);

  // Section 1: Participants
  const [participants, setParticipants] = useState<Participant[]>(['polymarket']);
  const [externalSources, setExternalSources] = useState<ExternalDataSource[]>([]);
  const [showAddSource, setShowAddSource] = useState(false);

  // Section 2: Strategy Intent
  const [selectedIntent, setSelectedIntent] = useState<StrategyIntent | null>(null);

  // Section 3: Observed Signals (dynamic)
  const [polymarketSignals, setPolymarketSignals] = useState({
    odds: true,
    order_book_depth: true,
    liquidity: true,
    market_status: true,
  });
  const [referenceSignals, setReferenceSignals] = useState({
    odds: true,
    market_availability: true,
  });
  const [truthSource, setTruthSource] = useState<'reference_market' | 'best_price' | 'weighted_avg'>('reference_market');

  // Section 4: Entry Rules
  const [entryRules, setEntryRules] = useState({
    event_finished: true,
    polymarket_unresolved: true,
    time_to_resolution_minutes: 120,
    min_liquidity_usdc: 2000,
    max_volatility_per_second: 0.0015,
  });

  // Section 5: Exclusion Rules
  const [exclusionRules, setExclusionRules] = useState({
    external_confirmation_ambiguous: true,
    market_suspended: true,
    volatility_spike: true,
    spread_threshold: 0.02,
  });

  // Section 6: Risk & Sizing
  const [riskConfig, setRiskConfig] = useState({
    max_per_event_usdc: 5000,
    max_total_exposure_usdc: 30000,
  });

  // Section 7: Advanced
  const [advancedExpanded, setAdvancedExpanded] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!user) return;

    const loadExternalSources = async () => {
      try {
        const api = initApiClient(createTokenGetter(user, stackApp));
        const sources = await api.get<ExternalDataSource[]>('/external-data-sources?is_active=true');
        setExternalSources(sources);
      } catch (err) {
        console.error('Error loading external sources:', err);
      }
    };

    loadExternalSources();
  }, [user, stackApp]);

  const handleSave = async () => {
    if (!user || !strategyName.trim()) return;

    setSaving(true);
    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      
      const strategyDefinition = {
        participants,
        intent: selectedIntent,
        signals: {
          polymarket: polymarketSignals,
          reference: referenceSignals,
          truth_source: truthSource,
        },
        entry_rules: entryRules,
        exclusion_rules: exclusionRules,
        risk_config: riskConfig,
      };

      const newStrategy = await api.post<{ id: string }>('/strategies', {
        name: strategyName,
        description: `Strategy intent: ${selectedIntent || 'custom'}`,
        decision_graph: { entry_node: 'start', nodes: {} },
        support_graphs: [],
        risk_config: riskConfig,
      });

      router.push(`/strategies/${newStrategy.id}/live`);
    } catch (err) {
      console.error('Error saving strategy:', err);
      alert(err instanceof Error ? err.message : 'Error al guardar estrategia');
    } finally {
      setSaving(false);
    }
  };

  const handleParticipantToggle = (participant: Participant) => {
    if (participant === 'polymarket') return;
    
    setParticipants(prev => 
      prev.includes(participant)
        ? prev.filter(p => p !== participant)
        : [...prev, participant]
    );
  };

  const estimatedConcurrentEvents = Math.floor(
    riskConfig.max_total_exposure_usdc / riskConfig.max_per_event_usdc
  );

  if (!user) return null;

  return (
    <Layout>
      <div className="h-screen flex flex-col bg-[#fafbfc] overflow-hidden">
        {/* Header - Fixed */}
        <div className="flex-shrink-0 bg-white/95 backdrop-blur-sm border-b border-[#e5e7eb]">
          <div className="max-w-[1600px] mx-auto px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex-1 flex items-center gap-4">
                <input
                  type="text"
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  className="text-2xl font-semibold text-[#111827] border-none outline-none bg-transparent w-full placeholder-[#9ca3af]"
                  placeholder="Untitled Strategy"
                />
                <span className={`px-3 py-1 rounded-md text-sm font-medium ${
                  status === 'DRAFT' ? 'bg-[#f3f4f6] text-[#374151]' :
                  status === 'ACTIVE' ? 'bg-[#d1fae5] text-[#065f46]' :
                  'bg-[#fef3c7] text-[#92400e]'
                }`}>
                  {status === 'DRAFT' ? 'Draft' : status === 'ACTIVE' ? 'Active' : 'Paused'}
                </span>
              </div>
              <button
                onClick={handleSave}
                disabled={saving || !strategyName.trim()}
                className="px-6 py-2.5 text-sm font-medium text-white bg-[#2563eb] rounded-lg hover:bg-[#1d4ed8] disabled:bg-[#9ca3af] disabled:cursor-not-allowed transition-all duration-200"
              >
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>

        {/* Main Content - 2 Column Layout */}
        <div className="flex-1 overflow-hidden">
          <div className="max-w-[1600px] mx-auto h-full px-8 py-6">
            <div className="h-full grid grid-cols-2 gap-8">
              
              {/* Left Column */}
              <div className="flex flex-col gap-6 overflow-y-auto pr-4">
                {/* Participants */}
                <section>
                  <h2 className="text-lg font-semibold text-[#111827] mb-4">Participants</h2>
                  <div className="space-y-2">
                    <div className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-[#f9fafb] transition-colors">
                      <div className="w-5 h-5 rounded border-2 border-[#2563eb] bg-[#2563eb] flex items-center justify-center flex-shrink-0">
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-medium text-[#111827]">Polymarket</div>
                        <div className="text-xs text-[#6b7280]">Execution venue</div>
                      </div>
                    </div>

                    {(['pinnacle', 'bet365'] as Participant[]).map((participant => (
                      <label key={participant} className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-[#f9fafb] cursor-pointer transition-colors">
                        <input
                          type="checkbox"
                          checked={participants.includes(participant)}
                          onChange={() => handleParticipantToggle(participant)}
                          className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <div className="flex-1">
                          <div className="text-sm text-[#111827] capitalize">{participant === 'pinnacle' ? 'Pinnacle' : 'Bet365'}</div>
                          <div className="text-xs text-[#6b7280]">{participants.includes(participant) ? 'Configured' : 'Not configured'}</div>
                        </div>
                        {participants.includes(participant) && (
                          <button className="text-xs text-[#2563eb] hover:text-[#1d4ed8] font-medium">Configure</button>
                        )}
                      </label>
                    )))}

                    {externalSources.slice(0, 3).map((source) => (
                      <label key={source.id} className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-[#f9fafb] cursor-pointer transition-colors">
                        <input
                          type="checkbox"
                          checked={participants.includes(`custom_api_${source.id}` as any)}
                          onChange={() => handleParticipantToggle(`custom_api_${source.id}` as any)}
                          className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-[#111827] truncate">{source.name}</div>
                          <div className="text-xs text-[#6b7280]">Custom API</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </section>

                {/* Strategy Intent */}
                <section>
                  <h2 className="text-lg font-semibold text-[#111827] mb-4">Strategy Intent</h2>
                  <div className="space-y-3">
                    {([
                      { id: 'liquidity_near_resolution', label: 'Liquidity Near Resolution', desc: 'Low risk · Minutes–Hours', detail: 'Provide liquidity after real-world outcome is known but before resolution.' },
                      { id: 'value_bets', label: 'Value Bets', desc: 'Medium risk · Pre-event', detail: 'Exploit mispriced odds vs reference markets.' },
                      { id: 'arbitrage', label: 'Arbitrage / Surebet', desc: 'Very low risk · Fast execution', detail: 'Exploit cross-market inconsistencies.' },
                      { id: 'custom', label: 'Custom / Advanced', desc: 'Full control', detail: 'Define your own strategy logic.' },
                    ] as const).map((intent) => (
                      <label key={intent.id} className={`block p-4 rounded-xl cursor-pointer transition-all ${
                        selectedIntent === intent.id
                          ? 'bg-[#eff6ff] ring-2 ring-[#2563eb]'
                          : 'bg-white hover:bg-[#f9fafb]'
                      }`}>
                        <input
                          type="radio"
                          name="intent"
                          value={intent.id}
                          checked={selectedIntent === intent.id}
                          onChange={() => setSelectedIntent(intent.id as StrategyIntent)}
                          className="sr-only"
                        />
                        <div className="flex items-start gap-3">
                          <div className={`w-5 h-5 rounded-full border-2 flex-shrink-0 mt-0.5 ${
                            selectedIntent === intent.id
                              ? 'border-[#2563eb] bg-[#2563eb]'
                              : 'border-[#d1d5db]'
                          }`}>
                            {selectedIntent === intent.id && (
                              <div className="w-full h-full rounded-full bg-white scale-50"></div>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-semibold text-[#111827] mb-1">{intent.label}</div>
                            <div className="text-xs text-[#6b7280] mb-1.5">{intent.desc}</div>
                            <div className="text-xs text-[#6b7280] leading-relaxed">{intent.detail}</div>
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </section>
              </div>

              {/* Right Column */}
              <div className="flex flex-col gap-6 overflow-y-auto pl-4 border-l border-[#e5e7eb]">
                {/* Observed Signals */}
                {selectedIntent && (
                  <section>
                    <h2 className="text-lg font-semibold text-[#111827] mb-4">Observed Signals</h2>
                    {selectedIntent === 'arbitrage' && participants.length > 1 ? (
                      <div className="space-y-5">
                        <div>
                          <div className="text-sm font-medium text-[#111827] mb-3">Polymarket</div>
                          <div className="grid grid-cols-2 gap-3 pl-1">
                            {Object.entries(polymarketSignals).map(([key, value]) => (
                              <label key={key} className="flex items-center gap-2.5 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={value}
                                  onChange={(e) => setPolymarketSignals(prev => ({ ...prev, [key]: e.target.checked }))}
                                  className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                                />
                                <span className="text-sm text-[#111827]">
                                  {key === 'odds' ? 'Odds' :
                                   key === 'order_book_depth' ? 'Order book depth' :
                                   key === 'liquidity' ? 'Liquidity' :
                                   key === 'market_status' ? 'Market status' : key}
                                </span>
                              </label>
                            ))}
                          </div>
                        </div>

                        <div>
                          <div className="text-sm font-medium text-[#111827] mb-3">Reference venue</div>
                          <div className="grid grid-cols-2 gap-3 pl-1">
                            {Object.entries(referenceSignals).map(([key, value]) => (
                              <label key={key} className="flex items-center gap-2.5 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={value}
                                  onChange={(e) => setReferenceSignals(prev => ({ ...prev, [key]: e.target.checked }))}
                                  className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                                />
                                <span className="text-sm text-[#111827]">
                                  {key === 'odds' ? 'Odds' :
                                   key === 'market_availability' ? 'Market availability' : key}
                                </span>
                              </label>
                            ))}
                          </div>
                          <div className="mt-4 pt-4 border-t border-[#e5e7eb]">
                            <div className="text-sm font-medium text-[#111827] mb-3">Truth source</div>
                            <div className="space-y-2 pl-1">
                              {[
                                { value: 'reference_market', label: 'Reference market' },
                                { value: 'best_price', label: 'Best available price' },
                                { value: 'weighted_avg', label: 'Weighted average' },
                              ].map((option) => (
                                <label key={option.value} className="flex items-center gap-2.5 cursor-pointer">
                                  <input
                                    type="radio"
                                    name="truth_source"
                                    value={option.value}
                                    checked={truthSource === option.value}
                                    onChange={() => setTruthSource(option.value as any)}
                                    className="w-5 h-5 text-[#2563eb] border-[#d1d5db] focus:ring-2 focus:ring-[#2563eb]"
                                  />
                                  <span className="text-sm text-[#111827]">{option.label}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : selectedIntent === 'liquidity_near_resolution' ? (
                      <div>
                        <div className="text-sm font-medium text-[#111827] mb-3">Polymarket</div>
                        <div className="grid grid-cols-2 gap-3 pl-1">
                          {Object.entries(polymarketSignals).map(([key, value]) => (
                            <label key={key} className="flex items-center gap-2.5 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={value}
                                onChange={(e) => setPolymarketSignals(prev => ({ ...prev, [key]: e.target.checked }))}
                                className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                              />
                              <span className="text-sm text-[#111827]">
                                {key === 'odds' ? 'Odds' :
                                 key === 'order_book_depth' ? 'Order book depth' :
                                 key === 'liquidity' ? 'Liquidity' :
                                 key === 'market_status' ? 'Market status' : key}
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </section>
                )}

                {/* Entry Rules */}
                {selectedIntent && (
                  <section>
                    <h2 className="text-lg font-semibold text-[#111827] mb-4">Entry Rules</h2>
                    <div className="space-y-3">
                      <label className="flex items-center gap-3 py-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={entryRules.event_finished}
                          onChange={(e) => setEntryRules(prev => ({ ...prev, event_finished: e.target.checked }))}
                          className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-sm text-[#111827]">Event finished in real world</span>
                      </label>

                      <label className="flex items-center gap-3 py-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={entryRules.polymarket_unresolved}
                          onChange={(e) => setEntryRules(prev => ({ ...prev, polymarket_unresolved: e.target.checked }))}
                          className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-sm text-[#111827]">Polymarket unresolved</span>
                      </label>

                      <div className="flex items-center gap-3 py-2 pl-8">
                        <span className="text-sm text-[#111827]">Time to resolution</span>
                        <input
                          type="number"
                          value={entryRules.time_to_resolution_minutes}
                          onChange={(e) => setEntryRules(prev => ({ ...prev, time_to_resolution_minutes: Number(e.target.value) }))}
                          className="w-24 px-3 py-2 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-xs text-[#6b7280]">minutes</span>
                      </div>

                      <div className="flex items-center gap-3 py-2 pl-8">
                        <span className="text-sm text-[#111827]">Liquidity ≥</span>
                        <input
                          type="number"
                          value={entryRules.min_liquidity_usdc}
                          onChange={(e) => setEntryRules(prev => ({ ...prev, min_liquidity_usdc: Number(e.target.value) }))}
                          className="w-32 px-3 py-2 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-xs text-[#6b7280]">USDC</span>
                      </div>

                      <div className="flex items-center gap-3 py-2 pl-8">
                        <span className="text-sm text-[#111827]">Short-term volatility ≤</span>
                        <input
                          type="number"
                          step="0.0001"
                          value={entryRules.max_volatility_per_second}
                          onChange={(e) => setEntryRules(prev => ({ ...prev, max_volatility_per_second: Number(e.target.value) }))}
                          className="w-32 px-3 py-2 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-xs text-[#6b7280]">/ second</span>
                      </div>
                    </div>
                  </section>
                )}

                {/* Exclusion Rules */}
                {selectedIntent && (
                  <section>
                    <h2 className="text-lg font-semibold text-[#111827] mb-4">Exclusion Rules</h2>
                    <div className="space-y-3">
                      <label className="flex items-center gap-3 py-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={exclusionRules.external_confirmation_ambiguous}
                          onChange={(e) => setExclusionRules(prev => ({ ...prev, external_confirmation_ambiguous: e.target.checked }))}
                          className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-sm text-[#111827]">External confirmation is ambiguous</span>
                      </label>

                      <label className="flex items-center gap-3 py-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={exclusionRules.market_suspended}
                          onChange={(e) => setExclusionRules(prev => ({ ...prev, market_suspended: e.target.checked }))}
                          className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-sm text-[#111827]">Market suspended</span>
                      </label>

                      <label className="flex items-center gap-3 py-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={exclusionRules.volatility_spike}
                          onChange={(e) => setExclusionRules(prev => ({ ...prev, volatility_spike: e.target.checked }))}
                          className="w-5 h-5 text-[#2563eb] border-[#d1d5db] rounded focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-sm text-[#111827]">Volatility spike detected</span>
                      </label>

                      <div className="flex items-center gap-3 py-2 pl-8">
                        <span className="text-sm text-[#111827]">Spread &gt;</span>
                        <input
                          type="number"
                          step="0.01"
                          value={exclusionRules.spread_threshold}
                          onChange={(e) => setExclusionRules(prev => ({ ...prev, spread_threshold: Number(e.target.value) }))}
                          className="w-28 px-3 py-2 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                        />
                        <span className="text-xs text-[#6b7280]">threshold</span>
                      </div>
                    </div>
                  </section>
                )}

                {/* Risk & Sizing */}
                {selectedIntent && (
                  <section>
                    <h2 className="text-lg font-semibold text-[#111827] mb-4">Risk & Sizing</h2>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-[#6b7280] mb-2">Max per event</label>
                        <div className="flex items-center gap-3">
                          <input
                            type="number"
                            value={riskConfig.max_per_event_usdc}
                            onChange={(e) => setRiskConfig(prev => ({ ...prev, max_per_event_usdc: Number(e.target.value) }))}
                            className="flex-1 px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                          />
                          <span className="text-sm text-[#6b7280]">USDC</span>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-[#6b7280] mb-2">Max total exposure</label>
                        <div className="flex items-center gap-3">
                          <input
                            type="number"
                            value={riskConfig.max_total_exposure_usdc}
                            onChange={(e) => setRiskConfig(prev => ({ ...prev, max_total_exposure_usdc: Number(e.target.value) }))}
                            className="flex-1 px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                          />
                          <span className="text-sm text-[#6b7280]">USDC</span>
                        </div>
                      </div>

                      <div className="px-4 py-3 bg-[#f0f9ff] rounded-lg">
                        <div className="text-sm text-[#0369a1] leading-relaxed">
                          With current settings, the strategy may operate on <strong>~{estimatedConcurrentEvents - 1}–{estimatedConcurrentEvents + 1} events</strong> simultaneously.
                        </div>
                      </div>
                    </div>
                  </section>
                )}

                {/* Advanced */}
                <section>
                  <button
                    onClick={() => setAdvancedExpanded(!advancedExpanded)}
                    className="w-full flex items-center justify-between py-2 hover:bg-[#f9fafb] rounded-lg px-2 -mx-2 transition-colors"
                  >
                    <div className="text-left">
                      <h2 className="text-lg font-semibold text-[#111827]">Advanced</h2>
                      <p className="text-xs text-[#6b7280]">AI generation, JSON preview, validation</p>
                    </div>
                    <span className="text-[#9ca3af]">{advancedExpanded ? '▼' : '▶'}</span>
                  </button>

                  {advancedExpanded && (
                    <div className="mt-4 space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-[#6b7280] mb-2">Generate from natural language</label>
                        <textarea
                          value={aiPrompt}
                          onChange={(e) => setAiPrompt(e.target.value)}
                          placeholder="Describe your strategy..."
                          className="w-full px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] resize-none"
                          rows={3}
                        />
                        <button
                          onClick={() => {
                            setGenerating(true);
                            setTimeout(() => setGenerating(false), 2000);
                          }}
                          disabled={!aiPrompt.trim() || generating}
                          className="mt-2 px-4 py-2 text-sm font-medium text-white bg-[#2563eb] rounded-lg hover:bg-[#1d4ed8] disabled:bg-[#9ca3af] disabled:cursor-not-allowed transition-all"
                        >
                          {generating ? 'Generating...' : 'Generate'}
                        </button>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-sm font-medium text-[#6b7280]">Strategy Definition (JSON)</label>
                          <button className="text-sm text-[#2563eb] hover:text-[#1d4ed8]">Validate</button>
                        </div>
                        <pre className="p-4 bg-[#f9fafb] border border-[#e5e7eb] rounded-lg text-xs text-[#111827] overflow-x-auto max-h-48">
                          {JSON.stringify({
                            participants,
                            intent: selectedIntent,
                            signals: {
                              polymarket: polymarketSignals,
                              reference: referenceSignals,
                              truth_source: truthSource,
                            },
                            entry_rules: entryRules,
                            exclusion_rules: exclusionRules,
                            risk_config: riskConfig,
                          }, null, 2)}
                        </pre>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-[#6b7280] mb-2">Explanation</label>
                        <div className="p-4 bg-[#f9fafb] border border-[#e5e7eb] rounded-lg text-sm text-[#111827] leading-relaxed">
                          {selectedIntent ? (
                            <>
                              This strategy targets <strong>{selectedIntent === 'liquidity_near_resolution' ? 'liquidity near resolution' : selectedIntent === 'value_bets' ? 'value bets' : selectedIntent === 'arbitrage' ? 'arbitrage opportunities' : 'custom opportunities'}</strong>.
                              {' '}It observes signals from {participants.length} participant{participants.length > 1 ? 's' : ''} and enters when all entry rules are met, while respecting exclusion rules.
                              {' '}Maximum exposure is {riskConfig.max_total_exposure_usdc.toLocaleString()} USDC with {riskConfig.max_per_event_usdc.toLocaleString()} USDC per event.
                            </>
                          ) : (
                            'Select a strategy intent to see the explanation.'
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </section>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
