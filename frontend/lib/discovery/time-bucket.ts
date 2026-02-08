/**
 * TimeBucket: max TTR (time to resolution) en minutos.
 * Usado en URLs /crypto/15M, /politics/1D
 */

export const TIME_BUCKET_MINUTES: Record<string, number> = {
  '5M': 5,
  '15M': 15,
  '1H': 60,
  '1D': 1440,
};

export function getTimeBucketMinutes(bucket: string): number | null {
  return TIME_BUCKET_MINUTES[bucket] ?? null;
}

export function isValidTimeBucket(bucket: string): boolean {
  return bucket in TIME_BUCKET_MINUTES;
}

export function getEndDateMaxIso(minutes: number): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() + minutes);
  return d.toISOString();
}
