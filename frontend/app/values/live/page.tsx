'use client';

import { useState } from 'react';
import { Layout } from '@/components/Layout';
import { GlobalSignalHeaderWithLoader } from '@/components/values/GlobalSignalHeaderWithLoader';
import { LiveValuesStreamWithLoader } from '@/components/values/LiveValuesStreamWithLoader';
import { EdgeDynamics } from '@/components/values/EdgeDynamics';
import { SourceHealthBreakdown } from '@/components/values/SourceHealthBreakdown';
import { SignalQualityPanel } from '@/components/values/SignalQualityPanel';
import { StrategyReadiness } from '@/components/values/StrategyReadiness';
import { SignalAlertsWithLoader } from '@/components/values/SignalAlertsWithLoader';
import { SignalLifecycleView } from '@/components/values/SignalLifecycleView';
import { HistoricalContext } from '@/components/values/HistoricalContext';
import type { ValueSignal } from '@/components/values/LiveValuesStream';

export default function ValuesLivePage() {
  const [selectedValue, setSelectedValue] = useState<ValueSignal | null>(null);

  return (
    <Layout>
      <div className="space-y-6 w-full">
        {/* 1. Global Signal Header - Carga independiente */}
        <GlobalSignalHeaderWithLoader />

        {/* 2. Live Values Stream - Carga independiente */}
        <LiveValuesStreamWithLoader onSelectValue={setSelectedValue} />

        {/* 3. Edge Dynamics (solo si hay value seleccionada) */}
        {selectedValue && (
          <div className="w-full">
            <EdgeDynamics value={selectedValue as any} />
          </div>
        )}

        {/* 4. Source Health Breakdown */}
        <div className="w-full">
          <SourceHealthBreakdown values={[]} selectedValue={selectedValue as any} />
        </div>

        {/* 5. Quality & Confidence Panel */}
        <div className="w-full">
          <SignalQualityPanel values={[]} selectedValue={selectedValue as any} />
        </div>

        {/* 6. Strategy Readiness */}
        <div className="w-full">
          <StrategyReadiness values={[]} />
        </div>

        {/* 7. Anomalies & Alerts - Carga independiente */}
        <SignalAlertsWithLoader />

        {/* 8. Signal Lifecycle View */}
        <div className="w-full">
          <SignalLifecycleView values={[]} />
        </div>

        {/* 9. Historical Context */}
        {selectedValue && (
          <div className="w-full">
            <HistoricalContext value={selectedValue as any} />
          </div>
        )}
      </div>
    </Layout>
  );
}
