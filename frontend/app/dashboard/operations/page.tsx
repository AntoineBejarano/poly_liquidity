'use client';

import { Layout } from '@/components/Layout';
import { OperationalAlertsList } from '@/components/operations/OperationalAlertsList';
import { StrategyStateDistribution } from '@/components/operations/StrategyStateDistribution';
import { StrategyStatusTable } from '@/components/operations/StrategyStatusTable';
import { InfrastructureHealthCards } from '@/components/operations/InfrastructureHealthCards';
import { ValuesSnapshotCard } from '@/components/operations/ValuesSnapshotCard';

export default function OperationsDashboardPage() {
  return (
    <Layout>
      <div className="space-y-6 w-full max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-h2">Operations Dashboard</h1>
            <p className="text-body text-muted-foreground mt-1">
              Centro de control operativo: estrategias activas, alertas y salud del sistema
            </p>
          </div>
        </div>

        {/* 1. Operational Alerts (High Priority) - Carga independiente */}
        <OperationalAlertsList />

        {/* 2. Strategy State Distribution - Carga independiente */}
        <StrategyStateDistribution />

        {/* 3. Active Strategies Overview - Carga independiente */}
        <StrategyStatusTable />

        {/* 4. Infrastructure Health & Values Snapshot - Carga independiente */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <InfrastructureHealthCards />
          <ValuesSnapshotCard />
        </div>
      </div>
    </Layout>
  );
}
