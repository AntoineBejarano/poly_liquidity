import { redirect } from 'next/navigation';
import { isValidDomainSlug } from '@/lib/discovery';
import { Layout } from '@/components/Layout';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const DEFAULT_TIME_BUCKET = '15M';

export default async function DomainRedirectPage({ params }: { params: Promise<{ domain?: string }> }) {
  const { domain } = await params;
  const domainSlug = domain ?? '';

  if (isValidDomainSlug(domainSlug)) {
    redirect(`/markets/${domainSlug}/${DEFAULT_TIME_BUCKET}`);
  }

  return (
    <Layout>
      <Alert variant="destructive">
        <AlertTitle>Dominio no válido</AlertTitle>
        <AlertDescription>
          Usa /markets/crypto/15M, /markets/politics/1D, etc.
        </AlertDescription>
      </Alert>
    </Layout>
  );
}
