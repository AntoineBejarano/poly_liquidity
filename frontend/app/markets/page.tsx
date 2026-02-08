'use client';

import { Layout } from '@/components/Layout';
import { DOMAIN_REGISTRY } from '@/lib/discovery/domain-registry';
import { LEAGUE_REGISTRY } from '@/lib/discovery/league-registry';
import { TIME_BUCKET_MINUTES } from '@/lib/discovery/time-bucket';
import Link from 'next/link';
import { TrendingUp, Landmark, Trophy, Radio } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function MarketsHubPage() {
  const domainsWithTimeBucket = DOMAIN_REGISTRY.filter((d) => d.supportsTimeBucket);
  const timeBucketSlugs = Object.keys(TIME_BUCKET_MINUTES);

  return (
    <Layout>
      <div className="space-y-6 p-4">
        <div>
          <h1 className="text-2xl font-semibold">Discovery</h1>
          <p className="text-muted-foreground mt-1">
            Explora mercados tradeables por categoría. URLs legibles, market-first.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Crypto & Politics (domains with time bucket) */}
          {domainsWithTimeBucket.map((domain) => (
            <Card key={domain.domainSlug} className="overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  {domain.category === 'crypto' ? (
                    <TrendingUp className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <Landmark className="h-5 w-5 text-muted-foreground" />
                  )}
                  <CardTitle className="text-lg capitalize">{domain.domainSlug}</CardTitle>
                </div>
                <CardDescription>
                  Mercados por tiempo hasta resolución (TTR)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Link
                  href={`/markets/${domain.domainSlug}/events`}
                  className="flex items-center gap-2 rounded-md border border-primary/50 bg-primary/5 px-3 py-2 text-sm font-medium text-primary transition-colors hover:bg-primary/10"
                >
                  Eventos
                </Link>
                {timeBucketSlugs.map((bucket) => (
                  <Link
                    key={bucket}
                    href={`/markets/${domain.domainSlug}/${bucket}`}
                    className="block rounded-md border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
                  >
                    {bucket}
                  </Link>
                ))}
              </CardContent>
            </Card>
          ))}

          {/* Sports — Leagues */}
          <Card className="overflow-hidden">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-muted-foreground" />
                <CardTitle className="text-lg">Sports</CardTitle>
              </div>
              <CardDescription>
                Partidos por liga
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {LEAGUE_REGISTRY.slice(0, 8).map((league) => (
                <Link
                  key={league.leagueSlug}
                  href={`/sports/${league.leagueSlug}/games`}
                  className="block rounded-md border px-3 py-2 text-sm font-medium uppercase transition-colors hover:bg-muted"
                >
                  {league.leagueSlug}
                </Link>
              ))}
              <Link
                href="/sports/live"
                className="mt-3 flex items-center gap-2 rounded-md border border-primary/50 bg-primary/5 px-3 py-2 text-sm font-medium text-primary transition-colors hover:bg-primary/10"
              >
                <Radio className="h-4 w-4" />
                Live
              </Link>
            </CardContent>
          </Card>
        </div>

        <div className="border-t pt-4">
          <Link
            href="/markets/legacy"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Búsqueda por series/etiquetas (legacy) →
          </Link>
        </div>
      </div>
    </Layout>
  );
}
