export { DiscoveryClient } from './discoveryClient';
export type { FetchMarketsParams, FetchMarketsResult, FetchEventsParams, FetchEventsResult, FetchDiscoveryParams, FetchDiscoveryResult } from './discoveryClient';
export * from './types';
export * from './transform';
export {
  DOMAIN_REGISTRY,
  getDomainBySlug,
  isValidDomainSlug,
} from './domain-registry';
export type { DomainEntry } from './domain-registry';
export {
  LEAGUE_REGISTRY,
  getLeagueBySlug,
  isValidLeagueSlug,
} from './league-registry';
export type { LeagueEntry } from './league-registry';
export {
  getTimeBucketMinutes,
  getEndDateMaxIso,
  isValidTimeBucket,
  TIME_BUCKET_MINUTES,
} from './time-bucket';
export {
  searchMarkets,
  normalizeForSearch,
  expandQuery,
  createSearchIndex,
  SEARCH_SYNONYMS,
} from './search';
