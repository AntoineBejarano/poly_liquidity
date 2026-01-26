# Plan: Carga Separada por Componente para Mejorar UX

## Objetivo

Implementar carga independiente para cada componente/sección de la aplicación, permitiendo:
- **Carga progresiva**: Los componentes aparecen tan pronto como sus datos están listos
- **Sin bloqueos**: Un componente lento no bloquea a los demás
- **Mejor UX**: El usuario ve contenido útil inmediatamente
- **Manejo granular de errores**: Errores en un componente no afectan a otros

---

## Estado Actual

### Problemas Identificados

1. **Páginas con carga monolítica**:
   - `dashboard/capital`: Carga dashboard, strategies, positions, metrics y equity history juntos
   - `dashboard/operations`: Carga todo en un solo `useDataLoader`
   - `values/live`: Carga múltiples fuentes de datos juntas

2. **Dependencias innecesarias**:
   - Cambiar un filtro recarga todos los datos
   - Un error en un endpoint bloquea toda la página

3. **UX subóptima**:
   - Pantalla en blanco mientras carga todo
   - No hay feedback granular del estado de carga

---

## Estrategia de Implementación

### Principio: "One Component, One Data Loader"

Cada componente visual que muestra datos debe tener su propio `useDataLoader` independiente.

### Patrón Base

```typescript
// ❌ MAL: Carga todo junto
const { data } = useDataLoader({
  fetchFn: async () => {
    const [data1, data2, data3] = await Promise.all([...]);
    return { data1, data2, data3 };
  }
});

// ✅ BIEN: Carga separada
const { data: data1 } = useDataLoader({ fetchFn: fetchData1 });
const { data: data2 } = useDataLoader({ fetchFn: fetchData2 });
const { data: data3 } = useDataLoader({ fetchFn: fetchData3 });
```

---

## Fase 1: Análisis y Auditoría

### Tareas

1. **Inventariar todas las páginas con carga de datos**
   - `app/dashboard/capital/page.tsx`
   - `app/dashboard/operations/page.tsx`
   - `app/values/live/page.tsx`
   - `app/strategies/[id]/live/page.tsx`
   - `app/strategies/[id]/page.tsx`
   - `app/markets/page.tsx`
   - Otras páginas que carguen datos

2. **Identificar dependencias entre datos**
   - ¿Qué datos dependen de otros?
   - ¿Qué datos pueden cargarse en paralelo?
   - ¿Qué datos deben esperar a otros?

3. **Mapear componentes visuales a datos**
   - Cada card/table/chart → su propio `useDataLoader`
   - Identificar componentes que comparten datos

---

## Fase 2: Refactorización por Página

### 2.1 Dashboard Capital (`app/dashboard/capital/page.tsx`)

#### Componentes a Separar

1. **Capital Overview Cards** (4 cards)
   - Total Equity
   - Available Liquidity
   - Capital at Risk
   - Pending Settlement
   - **Datos**: `/dashboard` endpoint
   - **Refresh**: Cada 10s

2. **Capital Allocation by Strategy Table**
   - **Datos**: `/strategies` + `/strategies/{id}/metrics` (uno por estrategia)
   - **Refresh**: Cada 10s
   - **Nota**: Puede cargar estrategias primero, luego métricas en paralelo

3. **PnL Breakdown by Strategy Table**
   - **Datos**: Mismo que arriba (comparte datos)
   - **Refresh**: Cada 10s

4. **Liquidity & Cash-Out Card**
   - **Datos**: Calculado desde `/dashboard` (comparte con Overview)
   - **Refresh**: Cada 10s

5. **Open Positions Table**
   - **Datos**: `/positions?resolved=false`
   - **Refresh**: Cada 10s

6. **Equity Curve Chart**
   - **Datos**: `/history/equity?range={timeRange}`
   - **Refresh**: Solo cuando cambia `timeRange` o manualmente
   - **Ya implementado separado** ✅

#### Estructura Propuesta

```typescript
// Componente principal
export default function CapitalDashboardPage() {
  // Cada sección tiene su propio loader
  return (
    <Layout>
      <CapitalOverviewCards />
      <CapitalAllocationTable />
      <PnLBreakdownTable />
      <LiquidityCard />
      <OpenPositionsTable />
      <EquityCurveChart />
    </Layout>
  );
}

// Cada componente maneja su propia carga
function CapitalOverviewCards() {
  const { data, isInitialLoading, isRefreshing } = useDataLoader({
    fetchFn: () => api.get('/dashboard'),
    refreshInterval: 10000,
  });
  
  if (isInitialLoading) return <CardSkeleton count={4} />;
  
  return (
    <div className="grid grid-cols-4">
      <EquityCard data={data} />
      <LiquidityCard data={data} />
      <RiskCard data={data} />
      <SettlementCard data={data} />
    </div>
  );
}
```

---

### 2.2 Dashboard Operations (`app/dashboard/operations/page.tsx`)

#### Componentes a Separar

1. **Strategy Status Table**
   - **Datos**: `/strategies` + `/live/status`
   - **Refresh**: Cada 10s

2. **Operational Alerts List**
   - **Datos**: `/live/status` (alerts)
   - **Refresh**: Cada 10s

3. **Infrastructure Health Cards**
   - **Datos**: `/live/status` (health)
   - **Refresh**: Cada 10s

4. **Values Snapshot Card**
   - **Datos**: `/values/live`
   - **Refresh**: Cada 10s

---

### 2.3 Values Live (`app/values/live/page.tsx`)

#### Componentes a Separar

1. **Global Signal Header**
   - **Datos**: `/values/live` (best edge, etc.)
   - **Refresh**: Cada 5s (más frecuente)

2. **Live Values Stream**
   - **Datos**: `/values/live` (stream)
   - **Refresh**: Cada 5s

3. **Active Signals List**
   - **Datos**: `/values/live` (signals)
   - **Refresh**: Cada 5s

---

### 2.4 Strategy Live (`app/strategies/[id]/live/page.tsx`)

#### Componentes a Separar

1. **Strategy Header**
   - **Datos**: `/strategies/{id}`
   - **Refresh**: Cada 30s (menos frecuente)

2. **Signals Monitor**
   - **Datos**: WebSocket `decision_trace`
   - **Refresh**: Real-time via WebSocket

3. **Execution Intents List**
   - **Datos**: `/strategies/{id}/executions`
   - **Refresh**: Cada 10s

4. **Strategy Metrics**
   - **Datos**: `/strategies/{id}/metrics`
   - **Refresh**: Cada 10s

---

## Fase 3: Componentes Reutilizables

### 3.1 Hook: `useComponentDataLoader`

Hook especializado para componentes que necesitan carga separada:

```typescript
interface UseComponentDataLoaderOptions<T> {
  fetchFn: () => Promise<T>;
  refreshInterval?: number;
  dependencies?: any[];
  enabled?: boolean;
  // Opciones específicas para componentes
  showSkeleton?: boolean;
  skeletonComponent?: React.ComponentType;
  showRefreshingIndicator?: boolean;
  onError?: (error: Error) => void;
}

function useComponentDataLoader<T>(options: UseComponentDataLoaderOptions<T>) {
  const { data, isInitialLoading, isRefreshing, error } = useDataLoader({
    fetchFn: options.fetchFn,
    refreshInterval: options.refreshInterval,
    dependencies: options.dependencies,
    enabled: options.enabled,
    onError: options.onError,
  });

  return {
    data,
    isInitialLoading,
    isRefreshing,
    error,
    // Helpers para renderizado
    renderSkeleton: options.showSkeleton && isInitialLoading 
      ? options.skeletonComponent 
      : null,
    renderRefreshingIndicator: options.showRefreshingIndicator && isRefreshing
      ? <RefreshingIndicator isRefreshing={true} />
      : null,
  };
}
```

### 3.2 Componente: `DataLoaderWrapper`

Wrapper genérico para componentes con carga de datos:

```typescript
interface DataLoaderWrapperProps<T> {
  fetchFn: () => Promise<T>;
  refreshInterval?: number;
  dependencies?: any[];
  enabled?: boolean;
  skeleton?: React.ComponentType;
  children: (data: T | null, isLoading: boolean, isRefreshing: boolean) => React.ReactNode;
  errorComponent?: React.ComponentType<{ error: Error }>;
}

function DataLoaderWrapper<T>({
  fetchFn,
  refreshInterval,
  dependencies,
  enabled,
  skeleton: Skeleton,
  children,
  errorComponent: ErrorComponent,
}: DataLoaderWrapperProps<T>) {
  const { data, isInitialLoading, isRefreshing, error } = useDataLoader({
    fetchFn,
    refreshInterval,
    dependencies,
    enabled,
  });

  if (error && ErrorComponent) {
    return <ErrorComponent error={error} />;
  }

  if (isInitialLoading && Skeleton) {
    return <Skeleton />;
  }

  return (
    <>
      {isRefreshing && <RefreshingIndicator isRefreshing={true} />}
      {children(data, isInitialLoading, isRefreshing)}
    </>
  );
}
```

---

## Fase 4: Optimizaciones

### 4.1 Carga Paralela vs Secuencial

**Regla**: Si los datos son independientes, cargar en paralelo. Si hay dependencias, cargar secuencialmente.

```typescript
// ✅ Paralelo: Datos independientes
const { data: strategies } = useDataLoader({ fetchFn: fetchStrategies });
const { data: positions } = useDataLoader({ fetchFn: fetchPositions });
const { data: dashboard } = useDataLoader({ fetchFn: fetchDashboard });

// ✅ Secuencial: Datos dependientes
const { data: strategy } = useDataLoader({ 
  fetchFn: () => fetchStrategy(strategyId),
  enabled: !!strategyId,
});
const { data: metrics } = useDataLoader({
  fetchFn: () => fetchStrategyMetrics(strategyId),
  enabled: !!strategy && !!strategyId, // Espera a que strategy cargue
  dependencies: [strategy],
});
```

### 4.2 Compartir Datos entre Componentes

**Problema**: Múltiples componentes necesitan los mismos datos.

**Solución**: Usar Context API o un hook compartido:

```typescript
// Hook compartido
function useSharedData<T>(
  key: string,
  fetchFn: () => Promise<T>,
  refreshInterval?: number
) {
  // Implementar cache compartido o Context
  // Evita múltiples llamadas al mismo endpoint
}

// Uso
const strategies = useSharedData('strategies', fetchStrategies, 10000);
const strategies2 = useSharedData('strategies', fetchStrategies); // Reutiliza cache
```

### 4.3 Priorización de Carga

**Estrategia**: Cargar primero lo más importante para el usuario.

```typescript
// Prioridad 1: Datos críticos (carga inmediata)
const { data: dashboard } = useDataLoader({ 
  fetchFn: fetchDashboard,
  priority: 'high', // Carga primero
});

// Prioridad 2: Datos secundarios (carga después)
const { data: metrics } = useDataLoader({
  fetchFn: fetchMetrics,
  priority: 'low', // Carga después
  enabled: !!dashboard, // Espera a dashboard
});
```

---

## Fase 5: Mejoras de UX

### 5.1 Skeletons Específicos por Componente

Cada componente tiene su skeleton personalizado:

```typescript
// Card skeleton específico
function EquityCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-16 mt-2" />
      </CardContent>
    </Card>
  );
}

// Table skeleton específico
function StrategyTableSkeleton() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {[1, 2, 3, 4].map(i => (
            <TableHead key={i}><Skeleton className="h-4 w-20" /></TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {[1, 2, 3, 4, 5].map(i => (
          <TableRow key={i}>
            {[1, 2, 3, 4].map(j => (
              <TableCell key={j}><Skeleton className="h-4 w-16" /></TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### 5.2 Indicadores de Estado Granulares

Cada componente muestra su propio estado:

```typescript
function StrategyTable() {
  const { data, isInitialLoading, isRefreshing, error } = useDataLoader({
    fetchFn: fetchStrategies,
  });

  return (
    <Card className="relative">
      {isRefreshing && (
        <div className="absolute top-2 right-2 z-10">
          <RefreshingIndicator isRefreshing={true} />
        </div>
      )}
      {error && (
        <div className="absolute top-2 left-2 z-10">
          <Alert variant="destructive">
            <AlertDescription>Error loading strategies</AlertDescription>
          </Alert>
        </div>
      )}
      {isInitialLoading ? (
        <StrategyTableSkeleton />
      ) : (
        <Table>...</Table>
      )}
    </Card>
  );
}
```

### 5.3 Manejo de Errores por Componente

Errores aislados no afectan otros componentes:

```typescript
function ComponentWithErrorHandling() {
  const { data, error } = useDataLoader({
    fetchFn: fetchData,
    onError: (err) => {
      // Log error pero no bloquear UI
      console.error('Component error:', err);
    },
  });

  if (error) {
    return (
      <Card>
        <CardContent>
          <Alert variant="destructive">
            <AlertDescription>
              Error loading data. <Button onClick={refetch}>Retry</Button>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return <ComponentContent data={data} />;
}
```

---

## Fase 6: Casos Especiales

### 6.1 Datos Dependientes

**Ejemplo**: Métricas de estrategia dependen de la estrategia.

```typescript
// Estrategia 1: Cargar secuencialmente
const { data: strategy } = useDataLoader({
  fetchFn: () => fetchStrategy(id),
  enabled: !!id,
});

const { data: metrics } = useDataLoader({
  fetchFn: () => fetchMetrics(id),
  enabled: !!strategy, // Espera a strategy
  dependencies: [strategy],
});

// Estrategia 2: Cargar en paralelo con validación
const { data: strategy } = useDataLoader({
  fetchFn: () => fetchStrategy(id),
  enabled: !!id,
});

const { data: metrics } = useDataLoader({
  fetchFn: () => fetchMetrics(id),
  enabled: !!id, // Carga en paralelo
  // Validar en el componente que strategy existe
});
```

### 6.2 Datos con Filtros

**Ejemplo**: Equity Curve con filtro de tiempo.

```typescript
const [timeRange, setTimeRange] = useState('30d');

// Carga separada - solo se recarga cuando cambia timeRange
const { data: equityHistory } = useDataLoader({
  fetchFn: () => fetchEquityHistory(timeRange),
  dependencies: [timeRange], // Solo este componente se recarga
  // No afecta otros componentes
});
```

### 6.3 Datos en Tiempo Real (WebSocket)

**Ejemplo**: Signals Monitor.

```typescript
// WebSocket no usa useDataLoader
function SignalsMonitor() {
  const [signals, setSignals] = useState({});
  
  useEffect(() => {
    const ws = useWebSocket('decision_trace');
    ws.on('message', (data) => {
      setSignals(data.signals);
    });
    return () => ws.close();
  }, []);

  return <SignalsDisplay signals={signals} />;
}
```

---

## Fase 7: Testing y Validación

### 7.1 Tests de Carga Separada

```typescript
describe('CapitalDashboardPage', () => {
  it('should load components independently', async () => {
    render(<CapitalDashboardPage />);
    
    // Verificar que cada componente carga independientemente
    expect(screen.getByText('Total Equity')).toBeInTheDocument();
    expect(screen.getByText('Capital Allocation')).toBeInTheDocument();
    // ...
  });

  it('should not reload all components when filter changes', async () => {
    const { rerender } = render(<CapitalDashboardPage />);
    
    // Cambiar filtro
    fireEvent.change(screen.getByLabelText('Time Range'), {
      target: { value: '7d' },
    });
    
    // Verificar que solo Equity Curve se recarga
    // Otros componentes no deberían mostrar loading
  });
});
```

### 7.2 Validación de Performance

- Medir tiempo de First Contentful Paint (FCP)
- Medir tiempo de carga de cada componente
- Verificar que no hay bloqueos innecesarios

---

## Orden de Implementación

### Sprint 1: Infraestructura
1. Crear `useComponentDataLoader` hook
2. Crear `DataLoaderWrapper` component
3. Crear skeletons específicos por componente

### Sprint 2: Dashboard Capital
1. Separar Capital Overview Cards
2. Separar Capital Allocation Table
3. Separar PnL Breakdown Table
4. Separar Open Positions Table
5. Equity Curve ya está separado ✅

### Sprint 3: Dashboard Operations
1. Separar Strategy Status Table
2. Separar Operational Alerts
3. Separar Infrastructure Health
4. Separar Values Snapshot

### Sprint 4: Otras Páginas
1. Values Live
2. Strategy Live
3. Markets Page
4. Strategy Detail

### Sprint 5: Optimizaciones
1. Implementar cache compartido
2. Priorización de carga
3. Mejoras de performance

---

## Métricas de Éxito

### UX
- ✅ Tiempo hasta primer contenido visible: < 500ms
- ✅ Componentes aparecen progresivamente
- ✅ Sin pantallas en blanco completas
- ✅ Errores aislados no bloquean la página

### Performance
- ✅ Tiempo de carga total: Reducido en 30%
- ✅ Tiempo de carga inicial: Reducido en 50%
- ✅ Sin bloqueos innecesarios

### Mantenibilidad
- ✅ Código más modular
- ✅ Fácil agregar nuevos componentes
- ✅ Tests más simples

---

## Consideraciones

### Ventajas
- ✅ Mejor UX (carga progresiva)
- ✅ Más resiliente (errores aislados)
- ✅ Más mantenible (código modular)
- ✅ Mejor performance (carga paralela)

### Desventajas
- ⚠️ Más hooks `useDataLoader` (más complejidad)
- ⚠️ Posible duplicación de llamadas (necesita cache compartido)
- ⚠️ Más código boilerplate (necesita componentes reutilizables)

### Mitigaciones
- Usar `useSharedData` para evitar duplicación
- Crear componentes wrapper reutilizables
- Documentar patrones claramente

---

## Conclusión

La carga separada por componente mejora significativamente la UX al permitir:
1. **Carga progresiva**: Los usuarios ven contenido útil inmediatamente
2. **Resiliencia**: Errores aislados no bloquean toda la página
3. **Performance**: Carga paralela y sin bloqueos innecesarios
4. **Mantenibilidad**: Código más modular y fácil de mantener

Este plan debe implementarse de forma incremental, empezando por las páginas más críticas (Dashboard Capital) y expandiéndose gradualmente.

