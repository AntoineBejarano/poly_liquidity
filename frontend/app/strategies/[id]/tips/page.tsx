'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import Link from 'next/link';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from '@/components/ui/sonner';
import {
  MessageSquare,
  ArrowLeft,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Play,
  Loader2,
  AlertCircle,
} from 'lucide-react';

interface TipIntentItem {
  id: string;
  strategy_id: string;
  status: string;
  raw_text: string | null;
  parsed: Record<string, unknown> | null;
  ps3838_event_id: string | null;
  ps3838_odds: number | null;
  suggested_stake_usd: number | null;
  risk_class: string | null;
  ps3838_bet_id: string | null;
  created_at: string | null;
  rejection_reason: string | null;
}

interface Summary {
  total: number;
  by_status: Record<string, number>;
}

export default function StrategyTipsPage() {
  const params = useParams();
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const strategyId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tips, setTips] = useState<TipIntentItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const fetchTips = async () => {
    if (!user || !stackApp) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    setError(null);
    try {
      const params = new URLSearchParams({ limit: '100' });
      if (statusFilter !== 'all') params.set('status', statusFilter);
      const [itemsRes, summaryRes] = await Promise.all([
        api.get<{ items: TipIntentItem[]; total: number }>(
          `/strategies/${strategyId}/tip-intents?${params}`
        ),
        api.get<Summary>(`/strategies/${strategyId}/tip-intents/summary`),
      ]);
      const data = itemsRes as { items?: TipIntentItem[]; total?: number };
      setTips(Array.isArray(data?.items) ? data.items : []);
      setSummary(summaryRes ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar tips');
      setTips([]);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!strategyId) return;
    setLoading(true);
    fetchTips();
  }, [strategyId, statusFilter, user, stackApp]);

  // WebSocket L2: tips en tiempo real (nuevo tip, resuelto, aprobado, etc.)
  useEffect(() => {
    if (!strategyId) return;
    setWsConnected(false);
    const raw = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const base = raw.trim().startsWith('http') ? raw.trim() : `https://${raw.replace(/^\/+/, '')}`;
    const wsUrl = base.replace(/^http/, 'ws') + `/ws/strategies/${strategyId}`;
    let ws: WebSocket | null = null;
    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => {
          setWsConnected(false);
          ws = null;
        };
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data as string);
            const t = msg?.type;
            if (t === 'tip_intent_created') {
              toast.info('Nuevo tip recibido');
              fetchTips();
            } else if (
              t === 'tip_intent_resolved' ||
              t === 'tip_intent_approved' ||
              t === 'tip_intent_rejected' ||
              t === 'tip_intent_executed'
            ) {
              fetchTips();
            }
          } catch {
            // ignore
          }
        };
      } catch {
        setWsConnected(false);
      }
    };
    connect();
    const interval = setInterval(() => {
      if (ws?.readyState === WebSocket.CLOSED) connect();
    }, 5000);
    return () => {
      clearInterval(interval);
      ws?.close();
      setWsConnected(false);
    };
  }, [strategyId]);

  const handleAction = async (
    tipId: string,
    action: 'resolve' | 'approve' | 'reject' | 'execute'
  ) => {
    if (!user || !stackApp) return;
    const api = initApiClient(createTokenGetter(user, stackApp));
    setActioningId(tipId);
    try {
      if (action === 'resolve') {
        await api.post(`/tip-intents/${tipId}/resolve`);
        toast.success('Match resolution ejecutado');
      } else if (action === 'approve') {
        await api.post(`/tip-intents/${tipId}/approve`);
        toast.success('Tip aprobado');
      } else if (action === 'reject') {
        await api.post(`/tip-intents/${tipId}/reject`, { reason: null });
        toast.success('Tip rechazado');
      } else if (action === 'execute') {
        await api.post(`/tip-intents/${tipId}/execute`);
        toast.success('Ejecución encolada');
      }
      await fetchTips();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : `Error en ${action}`);
    } finally {
      setActioningId(null);
    }
  };

  if (!user) return null;

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-5xl mx-auto pb-12">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Link
              href={`/strategies/${strategyId}`}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Volver a la estrategia
            </Link>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <MessageSquare className="h-7 w-7 text-primary" />
              Dashboard de Tips
              {wsConnected && (
                <Badge variant="secondary" className="font-normal text-xs">
                  En vivo
                </Badge>
              )}
            </h1>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { setLoading(true); fetchTips(); }}
            disabled={loading}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            <span className="ml-2">Actualizar</span>
          </Button>
        </div>

        {error && (
          <Card className="border-destructive/50 bg-destructive/5">
            <CardContent className="pt-6 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <p className="text-sm text-destructive">{error}</p>
              <Button variant="outline" size="sm" onClick={() => fetchTips()}>
                Reintentar
              </Button>
            </CardContent>
          </Card>
        )}

        {summary && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Resumen</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Total:</span>
                <span className="font-semibold">{summary.total}</span>
              </div>
              {Object.entries(summary.by_status || {}).map(([status, count]) => (
                <div key={status} className="flex items-center gap-2">
                  <Badge variant="outline">{status}</Badge>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Filtrar por estado:</span>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="PENDING">Pendientes</SelectItem>
              <SelectItem value="APPROVED">Aprobados</SelectItem>
              <SelectItem value="REJECTED">Rechazados</SelectItem>
              <SelectItem value="EXECUTED">Ejecutados</SelectItem>
              <SelectItem value="FAILED">Fallidos</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <LoadingSpinner />
            <p className="text-sm text-muted-foreground">Cargando tips…</p>
          </div>
        ) : tips.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
              <p className="text-sm text-muted-foreground">
                Aún no hay tips para esta estrategia.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Los tips aparecerán cuando el listener de Telegram reciba mensajes en los grupos configurados.
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Para recibir tips automáticamente, ejecuta el worker de Telegram (backend):{' '}
                <code className="bg-muted px-1 rounded text-[11px]">python -m app.workers.telegram_listener_worker --discover</code>
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {tips.map((tip) => (
              <Card key={tip.id} className="overflow-hidden">
                <CardContent className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1 space-y-1">
                      {tip.raw_text != null && tip.raw_text !== '' ? (
                        <p className="text-sm text-muted-foreground line-clamp-2">{tip.raw_text}</p>
                      ) : null}
                      {tip.parsed && typeof tip.parsed === 'object' && (
                        <div className="flex flex-wrap gap-2 text-xs">
                          {tip.parsed.partido != null && tip.parsed.partido !== '' ? (
                            <Badge variant="secondary">{String(tip.parsed.partido)}</Badge>
                          ) : null}
                          {tip.parsed.seleccion != null && tip.parsed.seleccion !== '' ? (
                            <Badge variant="outline">{String(tip.parsed.seleccion)}</Badge>
                          ) : null}
                          {tip.parsed.cuota != null ? (
                            <span className="text-muted-foreground">@ {String(tip.parsed.cuota)}</span>
                          ) : null}
                          {tip.suggested_stake_usd != null ? (
                            <span className="text-muted-foreground">{tip.suggested_stake_usd} u</span>
                          ) : null}
                          {tip.ps3838_odds != null ? (
                            <span className="text-muted-foreground">PS3838: {tip.ps3838_odds}</span>
                          ) : null}
                        </div>
                      )}
                      <div className="flex items-center gap-2 mt-2">
                        <Badge
                          variant={
                            tip.status === 'EXECUTED'
                              ? 'default'
                              : tip.status === 'REJECTED' || tip.status === 'FAILED'
                              ? 'destructive'
                              : tip.status === 'APPROVED'
                              ? 'secondary'
                              : 'outline'
                          }
                        >
                          {tip.status}
                        </Badge>
                        {tip.risk_class != null && tip.risk_class !== '' ? (
                          <span className="text-xs text-muted-foreground">{tip.risk_class}</span>
                        ) : null}
                        {tip.ps3838_bet_id != null && tip.ps3838_bet_id !== '' ? (
                          <span className="text-xs text-muted-foreground">Bet: {tip.ps3838_bet_id}</span>
                        ) : null}
                        {tip.created_at != null && tip.created_at !== '' ? (
                          <span className="text-xs text-muted-foreground">
                            {new Date(tip.created_at).toLocaleString()}
                          </span>
                        ) : null}
                      </div>
                      {tip.rejection_reason != null && tip.rejection_reason !== '' ? (
                        <p className="text-xs text-destructive mt-1">{tip.rejection_reason}</p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2 shrink-0">
                      {tip.status === 'PENDING' && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={actioningId === tip.id}
                            onClick={() => handleAction(tip.id, 'resolve')}
                          >
                            {actioningId === tip.id ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Resolver'}
                          </Button>
                          <Button
                            size="sm"
                            disabled={actioningId === tip.id}
                            onClick={() => handleAction(tip.id, 'approve')}
                          >
                            <CheckCircle2 className="h-4 w-4 mr-1" />
                            Aprobar
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={actioningId === tip.id}
                            onClick={() => handleAction(tip.id, 'reject')}
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Rechazar
                          </Button>
                        </>
                      )}
                      {tip.status === 'APPROVED' && (
                        <Button
                          size="sm"
                          disabled={actioningId === tip.id}
                          onClick={() => handleAction(tip.id, 'execute')}
                        >
                          {actioningId === tip.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 mr-1" />}
                          Ejecutar
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
