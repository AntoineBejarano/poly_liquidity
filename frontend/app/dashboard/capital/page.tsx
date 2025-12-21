'use client';

import { Layout } from '@/components/Layout';
import { CapitalOverviewCards } from '@/components/capital/CapitalOverviewCards';
import { CapitalAllocationTable } from '@/components/capital/CapitalAllocationTable';
import { PnLBreakdownTable } from '@/components/capital/PnLBreakdownTable';
import { LiquidityCard } from '@/components/capital/LiquidityCard';
import { OpenPositionsTable } from '@/components/capital/OpenPositionsTable';
import { EquityCurveChart } from '@/components/capital/EquityCurveChart';

export default function CapitalDashboardPage() {
  return (
    <Layout>
      <div className="space-y-6 w-full max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Capital Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Centro financiero: capital, PnL, liquidez y asignación por estrategia
            </p>
          </div>
        </div>

        {/* 1. Capital Overview Cards - Carga independiente */}
        <CapitalOverviewCards />

        {/* 2. Capital Allocation by Strategy - Carga independiente */}
        <CapitalAllocationTable />

        {/* 3. PnL Breakdown by Strategy - Carga independiente */}
        <PnLBreakdownTable />

        {/* 4. Liquidity & Cash-Out - Carga independiente */}
        <LiquidityCard />

        {/* 5. Open Positions - Carga independiente */}
        <OpenPositionsTable />

        {/* 6. Equity Curve - Carga independiente */}
        <EquityCurveChart />
      </div>
    </Layout>
  );
}
