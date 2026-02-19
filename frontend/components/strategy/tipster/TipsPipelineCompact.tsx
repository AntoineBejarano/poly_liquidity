'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { MessageSquare, ExternalLink } from 'lucide-react';

const STALENESS_THRESHOLD_MS = 30 * 1000; // 30 s

interface Summary {
  total: number;
  by_status: Record<string, number>;
}

interface TipsPipelineCompactProps {
  variant?: 'default' | 'compact';
}

export function TipsPipelineCompact({ variant = 'compact' }: TipsPipelineCompactProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();
  const params = useParams();
  const strategyId = params.id as string;

  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastFetchedAt, setLastFetchedAt] = useState<number>(0);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!user || !stackApp || !isConnected || !strategyId) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    const fetchSummary = async () => {
      try {
        const data = await api.get<Summary>(`/strategies/${strategyId}/tip-intents/summary`).catch(() => null);
        setSummary(data ?? null);
        setLastFetchedAt(Date.now());
      } catch {
        setSummary(null);
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
    const id = setInterval(fetchSummary, 5000);
    return () => clearInterval(id);
  }, [user, stackApp, isConnected, strategyId]);

  if (loading) {
    return (
      <div className="border-b border-border/40 py-4">
        <h3 className="text-h3 mb-2">Pipeline de Tips</h3>
        <div className="h-8 w-32 animate-pulse rounded bg-muted/50" />
      </div>
    );
  }

  const pending = summary?.by_status?.pending ?? 0;
  const executed = summary?.by_status?.executed ?? 0;
  const rejected = summary?.by_status?.rejected ?? 0;
  const total = summary?.total ?? 0;
  const isStale =
    lastFetchedAt > 0 && now - lastFetchedAt > STALENESS_THRESHOLD_MS;

  return (
    <div className="border-b border-border/40 py-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-h3 flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Pipeline de Tips
          {isStale && (
            <span
              className="text-[10px] text-amber-600 dark:text-amber-400 font-medium"
              title="Datos desactualizados (>30 s)"
            >
              Datos desactualizados
            </span>
          )}
        </h3>
        <Link
          href={`/strategies/${strategyId}/tips`}
          className="text-[12px] text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          Ver todos
          <ExternalLink className="h-3 w-3" />
        </Link>
      </div>
      <div className="flex items-center gap-4 text-[12px] tabular-nums">
        <span className="text-muted-foreground">
          Total: <span className="text-foreground font-medium">{total}</span>
        </span>
        <span>
          Pendientes: <span className="font-medium">{pending}</span>
        </span>
        <span>
          Ejecutados: <span className="font-medium text-primary">{executed}</span>
        </span>
        {rejected > 0 && (
          <span>
            Rechazados: <span className="font-medium text-destructive">{rejected}</span>
          </span>
        )}
      </div>
    </div>
  );
}
