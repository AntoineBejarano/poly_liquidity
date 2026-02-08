/**
 * DomainRegistry: dominios raíz para URLs.
 * - crypto: /markets/crypto/{timeBucket} (5M, 15M, 1H, 1D) — filtro por TTR.
 * - politics: /markets/politics/{tagSlug} (trump, venezuela, …) — filtro por tag (como Polymarket /politics/trump).
 * - finance: /markets/finance, /markets/finance/daily, /markets/finance/weekly — como Polymarket /finance, /finance/daily, /finance/weekly.
 */

export interface DomainEntry {
  domainSlug: string;
  gammaTagSlug: string;
  gammaTagId?: string;
  category: 'crypto' | 'politics' | 'finance' | 'general';
  /** true = segundo segmento es time bucket (crypto). */
  supportsTimeBucket: boolean;
  /** true = segundo segmento es tag slug para Gamma (politics). */
  supportsTagSlug?: boolean;
  /** true = segundo segmento es frecuencia (daily, weekly); API usa siempre gammaTagSlug. */
  supportsFrequencySegment?: boolean;
}

/** Tags de Politics en Polymarket (segundo segmento: /politics/trump, /politics/venezuela). */
export const POLITICS_TAG_SLUGS: { slug: string; label: string }[] = [
  { slug: 'trump', label: 'Trump' },
  { slug: 'venezuela', label: 'Venezuela' },
  { slug: 'epstein', label: 'Epstein' },
  { slug: 'midterms', label: 'Midterms' },
  { slug: 'primaries', label: 'Primaries' },
  { slug: 'us-election', label: 'US Election' },
  { slug: 'trade-war', label: 'Trade War' },
  { slug: 'congress', label: 'Congress' },
  { slug: 'ukraine', label: 'Ukraine' },
  { slug: 'gaza', label: 'Gaza' },
  { slug: 'israel', label: 'Israel' },
  { slug: 'cabinet', label: 'Cabinet' },
  { slug: 'senate', label: 'Senate' },
  { slug: 'courts', label: 'Courts' },
];

/** Finance: segmentos como Polymarket /finance/daily, /finance/weekly. */
export const FINANCE_FREQUENCY_SLUGS: { slug: string; label: string }[] = [
  { slug: 'daily', label: 'Daily' },
  { slug: 'weekly', label: 'Weekly' },
];

export const DOMAIN_REGISTRY: DomainEntry[] = [
  {
    domainSlug: 'crypto',
    gammaTagSlug: 'crypto',
    gammaTagId: '21',
    category: 'crypto',
    supportsTimeBucket: true,
  },
  {
    domainSlug: 'politics',
    gammaTagSlug: 'politics',
    category: 'politics',
    supportsTimeBucket: false,
    supportsTagSlug: true,
  },
  {
    domainSlug: 'finance',
    gammaTagSlug: 'finance',
    category: 'finance',
    supportsTimeBucket: false,
    supportsFrequencySegment: true,
  },
  {
    domainSlug: 'general',
    gammaTagSlug: '',
    category: 'general',
    supportsTimeBucket: false,
  },
];

export function getDomainBySlug(slug: string): DomainEntry | undefined {
  return DOMAIN_REGISTRY.find((d) => d.domainSlug === slug);
}

export function isValidDomainSlug(slug: string): boolean {
  return DOMAIN_REGISTRY.some((d) => d.domainSlug === slug);
}
