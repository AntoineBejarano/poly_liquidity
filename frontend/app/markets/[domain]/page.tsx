import { redirect } from 'next/navigation';
import { getDomainBySlug, isValidDomainSlug } from '@/lib/discovery';
import { Layout } from '@/components/Layout';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const DEFAULT_TIME_BUCKET = '15M';

export default async function DomainRedirectPage({ params }: { params: Promise<{ domain?: string }> }) {
  const { domain } = await params;
  const domainSlug = domain ?? '';

  if (isValidDomainSlug(domainSlug)) {
    const entry = getDomainBySlug(domainSlug);
    if (entry?.supportsTagSlug) {
      redirect(`/markets/${domainSlug}/events`);
    }
    redirect(`/markets/${domainSlug}/${DEFAULT_TIME_BUCKET}`);
  }

  return (
    <Layout>
      <Alert variant="destructive">
        <AlertTitle>Dominio no válido</AlertTitle>
        <AlertDescription>
          Crypto: /markets/crypto/15M. Politics: /markets/politics/trump. Finance: /markets/finance/daily, /markets/finance/weekly.
        </AlertDescription>
      </Alert>
    </Layout>
  );
}
