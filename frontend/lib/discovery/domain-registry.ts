/**
 * DomainRegistry: dominios raíz para URLs /{domain}/{timeBucket}
 * crypto, politics, general — usados en rutas tipo Polymarket /crypto/15M
 */

export interface DomainEntry {
  domainSlug: string;
  gammaTagSlug: string;
  gammaTagId?: string;
  category: 'crypto' | 'politics' | 'general';
  supportsTimeBucket: boolean;
}

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
    supportsTimeBucket: true,
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
