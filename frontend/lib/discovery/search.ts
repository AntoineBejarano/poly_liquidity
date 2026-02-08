/**
 * Search sobre candidatos Discovery (2 fases: URL → búsqueda local).
 * Normalización, sinónimos, Fuse.js para precisión percibida.
 */

import Fuse from 'fuse.js';
import type { IFuseOptions } from 'fuse.js';
import type { DiscoveryTradeableMarket } from './types';

/** Sinónimos: query → términos expandidos para matching */
export const SEARCH_SYNONYMS: Record<string, string[]> = {
  btc: ['bitcoin'],
  bitcoin: ['btc'],
  eth: ['ethereum'],
  ethereum: ['eth'],
  nfl: ['football'],
  football: ['nfl'],
  nba: ['basketball'],
  basketball: ['nba'],
  psg: ['paris saint germain', 'paris sg'],
  trump: ['donald trump'],
  sol: ['solana'],
  solana: ['sol'],
};

/** Normaliza texto para indexación: lowercasing, sin acentos, sin guiones */
export function normalizeForSearch(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ');
}

/** Expande query con sinónimos */
export function expandQuery(query: string): string {
  const q = normalizeForSearch(query);
  const parts = q.split(/\s+/).filter(Boolean);
  const expanded = new Set<string>(parts);
  for (const p of parts) {
    const syns = SEARCH_SYNONYMS[p];
    if (syns) {
      for (const s of syns) {
        expanded.add(s);
      }
    }
  }
  return Array.from(expanded).join(' ');
}

/** Genera texto indexable para un market (question + event_title + tags + series) */
export function getSearchableText(m: DiscoveryTradeableMarket): string {
  const parts: string[] = [m.question ?? '', m.event_title ?? ''];
  for (const t of m.event_tags ?? []) {
    parts.push(t.label ?? '', t.slug ?? '');
  }
  if (m.series_slug) parts.push(m.series_slug);
  return parts.filter(Boolean).join(' ');
}

const FUSE_OPTIONS: IFuseOptions<DiscoveryTradeableMarket> = {
  keys: [
    { name: 'question', weight: 1.2 },
    { name: 'event_title', weight: 1.0 },
    { name: 'event_tags_search', weight: 0.8 },
  ],
  threshold: 0.4,
  includeScore: true,
};

/** Crea índice Fuse a partir de candidatos */
export function createSearchIndex(markets: DiscoveryTradeableMarket[]): Fuse<DiscoveryTradeableMarket> {
  const items = markets.map((m) => ({
    ...m,
    event_tags_search: (m.event_tags ?? []).map((t) => (t.label ?? '') + ' ' + (t.slug ?? '')).join(' '),
  }));
  return new Fuse(items, FUSE_OPTIONS);
}

/** Busca en candidatos; expande query con sinónimos */
export function searchMarkets(
  markets: DiscoveryTradeableMarket[],
  query: string
): DiscoveryTradeableMarket[] {
  const q = query.trim();
  if (!q) return markets;

  const expanded = expandQuery(q);
  const fuse = createSearchIndex(markets);
  const results = fuse.search(expanded);

  return results.map((r) => r.item);
}
