'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SportsLiveEventState } from '@/lib/discovery/types';

/**
 * Actualización en vivo de un partido desde el Sports WebSocket de Polymarket (sport_result message).
 * @see https://docs.polymarket.com/developers/sports-websocket/overview
 * @see https://docs.polymarket.com/developers/sports-websocket/message-format
 */
export interface SportsLiveUpdate {
  gameId: number;
  /** Slug formato {league}-{team1}-{team2}-{date} (ej. nfl-buf-kc-2025-01-26) */
  slug?: string;
  leagueAbbreviation?: string;
  homeTeam: string;
  awayTeam: string;
  status: string;
  live: boolean;
  ended: boolean;
  score: string;
  period: string;
  elapsed?: string;
  finished_timestamp?: string;
  turn?: string;
}

/** Result of matching a discovery event to a sport_result. Only show score/period when confidence is 'high'. */
export interface MatchEventToSportResultResult {
  update: SportsLiveUpdate;
  confidence: 'high' | 'low';
}

/** Del WS: evento en vivo = status "InProgress". Más fiable que tiempo o cualquier otro filtro. */
const STATUS_IN_PROGRESS = 'InProgress';

export function isLiveFromWs(update: SportsLiveUpdate): boolean {
  return update.status === STATUS_IN_PROGRESS;
}

const WS_URL = 'wss://sports-api.polymarket.com/ws';
const PONG_TIMEOUT_MS = 10_000;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export interface UseSportsWebSocketResult {
  /** Todas las actualizaciones recibidas, key = slug o gameId */
  updatesByKey: Map<string, SportsLiveUpdate>;
  /** Slugs/gameIds que están en vivo ahora (status === "InProgress" desde el WS) */
  liveKeys: Set<string>;
  /** Estado de la conexión */
  connectionStatus: 'connecting' | 'open' | 'closed' | 'error';
  /** Reconectar manualmente */
  reconnect: () => void;
}

function isPingMessage(data: string | Buffer | ArrayBuffer | Blob): boolean {
  if (typeof data === 'string') return data === 'ping';
  return false;
}

function parseMessage(data: string | Buffer | ArrayBuffer | Blob): SportsLiveUpdate | null {
  if (typeof data !== 'string' || data === 'ping') return null;
  try {
    const obj = JSON.parse(data) as Record<string, unknown>;
    const gameId = Number(obj.gameId);
    if (Number.isNaN(gameId)) return null;
    const slug =
      typeof obj.slug === 'string'
        ? obj.slug
        : undefined;
    const homeTeam = typeof obj.homeTeam === 'string' ? obj.homeTeam : '';
    const awayTeam = typeof obj.awayTeam === 'string' ? obj.awayTeam : '';
    return {
      gameId,
      slug,
      leagueAbbreviation: typeof obj.leagueAbbreviation === 'string' ? obj.leagueAbbreviation : undefined,
      homeTeam,
      awayTeam,
      status: typeof obj.status === 'string' ? obj.status : '',
      live: obj.live === true,
      ended: obj.ended === true,
      score: typeof obj.score === 'string' ? obj.score : '',
      period: typeof obj.period === 'string' ? obj.period : '',
      elapsed: typeof obj.elapsed === 'string' ? obj.elapsed : undefined,
      finished_timestamp: typeof obj.finished_timestamp === 'string' ? obj.finished_timestamp : undefined,
      turn: typeof obj.turn === 'string' ? obj.turn : undefined,
    };
  } catch {
    return null;
  }
}

function getUpdateKey(u: SportsLiveUpdate): string {
  return u.slug ?? `game:${u.gameId}`;
}

/**
 * Hook que se conecta al Sports WebSocket de Polymarket para recibir resultados
 * en vivo (score, period, elapsed). Responde PING con PONG para mantener la conexión.
 */
export function useSportsWebSocket(enabled: boolean = true): UseSportsWebSocketResult {
  const [updatesByKey, setUpdatesByKey] = useState<Map<string, SportsLiveUpdate>>(() => new Map());
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'open' | 'closed' | 'error'>('closed');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(RECONNECT_BASE_MS);

  const connect = useCallback(() => {
    if (!enabled) return;
    setConnectionStatus('connecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('open');
      reconnectDelayRef.current = RECONNECT_BASE_MS;
    };

    ws.onmessage = (event: MessageEvent) => {
      if (isPingMessage(event.data)) {
        if (ws.readyState === WebSocket.OPEN) ws.send('pong');
        return;
      }
      const update = parseMessage(event.data);
      if (!update) return;
      const key = getUpdateKey(update);
      if (typeof process !== 'undefined' && process.env.NODE_ENV === 'development') {
        const kind = update.ended ? 'finished' : update.live ? 'live' : 'update';
        console.debug(LOG_PREFIX, `sport_result ${kind}`, key, update.score, update.period);
      }
      setUpdatesByKey((prev) => {
        const next = new Map(prev);
        next.set(key, update);
        return next;
      });
    };

    ws.onclose = () => {
      wsRef.current = null;
      setConnectionStatus('closed');
      if (!enabled) return;
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectDelayRef.current = Math.min(
          reconnectDelayRef.current * 2,
          RECONNECT_MAX_MS
        );
        connect();
      }, reconnectDelayRef.current);
    };

    ws.onerror = () => setConnectionStatus('error');
  }, [enabled]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus('closed');
  }, []);

  useEffect(() => {
    if (enabled) connect();
    return () => disconnect();
  }, [enabled, connect, disconnect]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectDelayRef.current = RECONNECT_BASE_MS;
    if (enabled) setTimeout(() => connect(), 0);
  }, [enabled, connect, disconnect]);

  const liveKeys = new Set<string>();
  updatesByKey.forEach((u, key) => {
    if (isLiveFromWs(u)) liveKeys.add(key);
  });

  return {
    updatesByKey,
    liveKeys,
    connectionStatus,
    reconnect,
  };
}

const LOG_PREFIX = '[SportsLive]';

/** Normalizar para matching: minúsculas y sin acentos */
function normalizeForMatch(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '');
}

/** Quitar prefijos/sufijos comunes (CA , FC, CF) para que Gamma y WS matcheen */
function teamNameCore(s: string): string {
  return s
    .replace(/\s+(cf|fc)$/i, '')
    .replace(/^(ca\s+|fc\s+|cf\s+|fk\s+|as\s+)/i, '')
    .trim();
}

/**
 * Matching dinámico: normaliza, quita prefijos/sufijos, exige título con nombre completo
 * o todas las palabras (≥2 chars) del equipo para que matcheen eventos Gamma y veamos mercados.
 */
function teamMatchesTitle(teamKey: string, title: string): boolean {
  const titleNorm = normalizeForMatch(title);
  const core = normalizeForMatch(teamNameCore(teamKey));
  if (core.length < 2) return false;
  if (titleNorm.includes(core)) return true;
  const words = core.split(/\s+/).filter((w) => w.length >= 2);
  if (words.length <= 1) return false;
  return words.every((w) => titleNorm.includes(w));
}

/**
 * Centralized event-to-sport_result matching. Used to decide WS_CONFIRMED_LIVE / WS_CONFIRMED_FINISHED.
 * TODO: Migrate to stable identifiers (external_game_id, or league+home+away+start_time) when API provides them.
 * Only show score/period in UI when confidence is 'high'.
 */
export function matchEventToSportResult(
  eventTitle: string,
  updatesByKey: Map<string, SportsLiveUpdate>
): MatchEventToSportResultResult | null {
  const title = (eventTitle ?? '').trim().toLowerCase();
  if (!title) return null;
  for (const u of updatesByKey.values()) {
    const home = (u.homeTeam ?? '').trim().toLowerCase();
    const away = (u.awayTeam ?? '').trim().toLowerCase();
    if (!home || !away) continue;
    const homeOk = teamMatchesTitle(u.homeTeam ?? '', title);
    const awayOk = teamMatchesTitle(u.awayTeam ?? '', title);
    if (!homeOk || !awayOk) continue;
    const confidence: 'high' | 'low' = home.length >= 2 && away.length >= 2 ? 'high' : 'low';
    return { update: u, confidence };
  }
  return null;
}

/**
 * Computes final EventState for an event. Priority: WS-confirmed first, then backend live_estimated, else NOT_LIVE.
 * Connection status is separate and must NOT be used to infer event state.
 */
export function computeEventState(
  eventTitle: string,
  liveEstimated: boolean | null | undefined,
  updatesByKey: Map<string, SportsLiveUpdate>
): SportsLiveEventState {
  const match = matchEventToSportResult(eventTitle, updatesByKey);
  if (match) {
    const { update } = match;
    if (update.ended) return 'WS_CONFIRMED_FINISHED';
    if (isLiveFromWs(update)) return 'WS_CONFIRMED_LIVE';
  }
  if (liveEstimated === true) return 'TIME_BASED_LIVE_ESTIMATED';
  return 'NOT_LIVE';
}

/**
 * Returns the sport_result update only when event is WS_CONFIRMED_LIVE and matching confidence is high.
 * Use this for displaying score/period; do not show score/period for LIVE_ESTIMATED or low confidence.
 */
export function getLiveUpdateForDisplay(
  eventTitle: string,
  liveEstimated: boolean | null | undefined,
  updatesByKey: Map<string, SportsLiveUpdate>
): SportsLiveUpdate | null {
  const state = computeEventState(eventTitle, liveEstimated, updatesByKey);
  if (state !== 'WS_CONFIRMED_LIVE') return null;
  const match = matchEventToSportResult(eventTitle, updatesByKey);
  if (!match || match.confidence !== 'high') return null;
  return match.update;
}

/** Lista de todos los partidos en vivo según el WS (status InProgress), dinámica. */
export function getLiveUpdatesList(updatesByKey: Map<string, SportsLiveUpdate>): SportsLiveUpdate[] {
  const list: SportsLiveUpdate[] = [];
  updatesByKey.forEach((u) => {
    if (isLiveFromWs(u)) list.push(u);
  });
  return list;
}
