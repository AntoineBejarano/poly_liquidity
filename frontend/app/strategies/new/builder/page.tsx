'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser, useStackApp } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useBackendConnection } from '@/hooks/useBackendConnection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Workflow } from 'lucide-react';

export default function NewStrategyBuilderPage() {
  const router = useRouter();
  const user = useUser();
  const stackApp = useStackApp();
  const { isConnected } = useBackendConnection();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateAndOpenBuilder = async () => {
    if (!name.trim()) {
      setError('El nombre de la estrategia es requerido');
      return;
    }

    if (!user) {
      setError('Debes estar autenticado');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const api = initApiClient(createTokenGetter(user, stackApp));

      // Create strategy with empty graph
      const strategy = await api.post('/strategies', {
        name: name.trim(),
        description: description.trim() || undefined,
        decision_graph: {
          nodes: [],
          edges: [],
        },
        support_graphs: [],
        control_loop_config: {},
        risk_config: {},
        tags: ['builder'],
      });

      // Redirect to builder
      router.push(`/strategies/${strategy.id}/builder`);
    } catch (err) {
      console.error('Error creating strategy:', err);
      setError(err instanceof Error ? err.message : 'Error al crear la estrategia');
      setLoading(false);
    }
  };

  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-2xl mx-auto pb-12">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Workflow className="h-6 w-6" />
            Nueva Estrategia - Custom Builder
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Crea una estrategia personalizada usando el graph-based builder
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>Información Básica</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nombre de la Estrategia *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej: My Custom Strategy"
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Descripción (opcional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe tu estrategia..."
                rows={3}
                disabled={loading}
              />
            </div>

            <div className="pt-4 flex items-center justify-between">
              <Button
                variant="outline"
                onClick={() => router.back()}
                disabled={loading}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleCreateAndOpenBuilder}
                disabled={loading || !name.trim()}
              >
                {loading ? (
                  'Creando...'
                ) : (
                  <>
                    Crear y Abrir Builder
                    <Workflow className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2 text-sm text-muted-foreground">
              <p className="font-medium text-foreground">Sobre el Builder:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Conecta bloques de trading predefinidos (Data Sources, Signals, Strategy Logic, Risk, Execution)</li>
                <li>El grafo debe ser un DAG válido que termine en nodos de ejecución</li>
                <li>Puedes ajustar parámetros de cada nodo desde el panel Inspector</li>
                <li>El JSON del grafo es la fuente de verdad y se guarda automáticamente</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

