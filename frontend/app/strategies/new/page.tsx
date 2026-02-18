'use client';

import { useRouter } from 'next/navigation';
import { useUser } from '@stackframe/stack';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowRight, Zap, TrendingUp, Target, Workflow, MessageSquare, BarChart3 } from 'lucide-react';

const STRATEGY_TEMPLATES = [
  {
    id: 'Liquidity',
    name: 'Liquidity Near Resolution',
    description: 'Provee liquidez cuando un evento ya terminó pero aún no ha sido resuelto por Polymarket. Captura el diferencial con riesgo casi nulo.',
    icon: Zap,
    href: '/strategies/new/Liquidity',
    risk: 'Low',
    timeframe: 'Minutes–Hours',
  },
  {
    id: 'Surebet',
    name: 'Surebet / Cross-Market Arbitrage',
    description: 'Explota ineficiencias de precio entre dos venues (Polymarket y Pinnacle). Ejecuta compras/ventas coordinadas con control estricto de riesgo y latencia.',
    icon: TrendingUp,
    href: '/strategies/new/Surebet',
    risk: 'Very Low',
    timeframe: 'Fast execution',
  },
  {
    id: 'TelegramTipster',
    name: 'Telegram Tipsters → PS3838',
    description: 'Conecta Telegram para seguir grupos de tipsters, extrae tips (partido, selección, stake) y ejecuta apuestas en PS3838 con control de riesgo y confirmación opcional.',
    icon: MessageSquare,
    href: '/strategies/create?template=telegram_tipster_ps3838',
    risk: 'Configurable',
    timeframe: 'Real-time',
  },
  {
    id: 'Values',
    name: 'Values Configuration',
    description: 'Define qué se considera "value" y bajo qué condiciones una señal es válida, visible y accionable. Configuración de señales de valor independiente de estrategias.',
    icon: Target,
    href: '/strategies/new/Values',
    risk: 'Signal Definition',
    timeframe: 'Configuration',
  },
  {
    id: 'Builder',
    name: 'Custom Builder',
    description: 'Crea una estrategia personalizada usando el graph-based builder. Conecta bloques de trading predefinidos para diseñar tu propia lógica de ejecución.',
    icon: Workflow,
    href: '/strategies/new/builder',
    risk: 'Advanced',
    timeframe: 'Custom',
  },
];

export default function NewStrategyPage() {
  const router = useRouter();
  const user = useUser();

  if (!user) return null;

  return (
    <Layout>
      <div className="space-y-6 w-full max-w-4xl mx-auto pb-12">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">Nueva Estrategia</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Selecciona un template para comenzar a configurar tu estrategia
          </p>
        </div>

        {/* Template Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {STRATEGY_TEMPLATES.map((template) => {
            const Icon = template.icon;
            return (
              <div
                key={template.id}
                role="button"
                tabIndex={0}
                onClick={() => router.push(template.href)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    router.push(template.href);
                  }
                }}
                className="cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-lg transition-all duration-200 ease-out hover:scale-[1.03] hover:-translate-y-1 hover:shadow-xl active:scale-[0.99] active:translate-y-0"
              >
                <Card className="h-full border-2 border-border hover:border-primary/50 transition-colors duration-200">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          <Icon className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{template.name}</CardTitle>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs px-2 py-0.5 bg-muted rounded">
                              {template.risk} risk
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {template.timeframe}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                      {template.description}
                    </p>
                    <Button
                      type="button"
                      className="w-full pointer-events-none"
                      aria-hidden
                    >
                      Seleccionar Template
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </CardContent>
                </Card>
              </div>
            );
          })}
        </div>

        {/* Info */}
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Cada template incluye una configuración guiada paso a paso. Una vez configurada, 
              podrás activar la estrategia y monitorearla en tiempo real desde el Live Control.
            </p>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
