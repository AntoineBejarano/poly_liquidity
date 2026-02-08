/**
 * LeagueRegistry: ligas para URLs /sports/{league}/games
 * nfl, nba, ncaab, nhl, ufc — usados dentro del contexto sports
 */

export interface LeagueEntry {
  leagueSlug: string;
  gammaTagSlug: string;
  gammaTagId?: string;
}

export const LEAGUE_REGISTRY: LeagueEntry[] = [
  { leagueSlug: 'nfl', gammaTagSlug: 'nfl' },
  { leagueSlug: 'nba', gammaTagSlug: 'nba' },
  { leagueSlug: 'ncaab', gammaTagSlug: 'ncaab' },
  { leagueSlug: 'nhl', gammaTagSlug: 'nhl' },
  { leagueSlug: 'ufc', gammaTagSlug: 'ufc' },
  { leagueSlug: 'soccer', gammaTagSlug: 'soccer' },
  { leagueSlug: 'tennis', gammaTagSlug: 'tennis' },
  { leagueSlug: 'esports', gammaTagSlug: 'esports' },
  { leagueSlug: 'baseball', gammaTagSlug: 'baseball' },
  { leagueSlug: 'hockey', gammaTagSlug: 'hockey' },
  { leagueSlug: 'cricket', gammaTagSlug: 'cricket' },
  { leagueSlug: 'rugby', gammaTagSlug: 'rugby' },
  { leagueSlug: 'golf', gammaTagSlug: 'golf' },
  { leagueSlug: 'formula1', gammaTagSlug: 'formula-1' },
];

export function getLeagueBySlug(slug: string): LeagueEntry | undefined {
  return LEAGUE_REGISTRY.find((l) => l.leagueSlug === slug);
}

export function isValidLeagueSlug(slug: string): boolean {
  return LEAGUE_REGISTRY.some((l) => l.leagueSlug === slug);
}
