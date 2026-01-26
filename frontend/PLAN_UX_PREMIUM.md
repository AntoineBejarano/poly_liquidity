# Plan UX Premium - AlphaEdge Trading Platform
## Transformación a nivel Railway/Vercel

**Fecha**: 2025-12-20
**Objetivo**: Elevar el frontend a un nivel ultra-premium con diseño minimalista, flujo perfecto y estilo Railway/Vercel

---

## 📊 Análisis del Estado Actual

### ✅ Lo que ya está BIEN (7/10)
- shadcn/ui al 100% - excelente base
- Dark mode con 4 variantes (light/dark/black/system)
- 7 gráficas profesionales con Recharts
- Skeleton loading states implementados
- Componentes TypeScript con type-safety
- Iconografía consistente (Lucide)
- Sistema de tokens CSS iniciado

### ❌ Problemas CRÍTICOS detectados

#### 1. **CONFLICTO DE SISTEMAS DE COLOR** 🔴 BLOCKER
**Archivo**: `frontend/app/globals.css`

**Problema**: Existen DOS sistemas de color compitiendo:
- **Sistema Custom** (líneas 1-23): `--color-surface`, `--color-text-primary`, etc.
- **Sistema shadcn/ui** (variables semánticas): `--background`, `--foreground`, etc.

**Impacto**:
- El Sidebar usa colores hardcoded (`bg-[#f3f4f6]`, `text-[#6b7280]`) en líneas 62-108
- Dark mode NO funciona en Sidebar
- Inconsistencia visual entre componentes
- Mantenimiento duplicado

**Evidencia**:
```tsx
// Sidebar.tsx:80-82 - HARDCODED ❌
className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
  isActive
    ? 'bg-[#f3f4f6] text-[#111827] font-medium'  // ❌ Hardcoded
    : 'text-[#6b7280] hover:bg-[#f9fafb]'        // ❌ Hardcoded
}`}
```

#### 2. **TIPOGRAFÍA INCONSISTENTE** 🟡
- Clases custom (`.text-title`, `.text-heading`) en `globals.css`
- Clases Tailwind (`text-2xl`, `text-sm`) mezcladas
- Sin sistema de jerarquía visual claro (h1, h2, h3, body, caption)

#### 3. **FALTA COMMAND PALETTE** 🟡
- Railway/Vercel tienen Cmd+K
- Sin búsqueda global
- Sin shortcuts de teclado visibles

#### 4. **EMPTY STATES POBRES** 🟡
- Mensajes genéricos "No hay estrategias"
- Sin ilustraciones
- Sin CTAs claros

#### 5. **SPACING NO ESTANDARIZADO** 🟡
- Algunos usan `p-6`, otros `p-4`, otros `p-24`
- Sin escala de espaciado consistente (debería ser 4, 8, 12, 16, 24, 32, 48, 64)

#### 6. **BREADCRUMBS AUSENTES** 🟡
- Navegación anidada sin contexto
- Componente Breadcrumb existe en shadcn/ui pero NO se usa

---

## 🎯 Plan de Transformación UX Premium

### **FASE 1: FUNDACIÓN SÓLIDA** (2-3 días)
*Arreglar problemas estructurales que bloquean el diseño premium*

#### 1.1 Consolidar Sistema de Color ⚡ CRÍTICO
**Objetivo**: Un único sistema de tokens semánticos

**Tareas**:
- [ ] **ELIMINAR** todas las variables custom del `@theme` en globals.css (líneas 3-23)
- [ ] **MIGRAR** a SOLO shadcn/ui semantic tokens:
  ```css
  /* Usar SOLO estos tokens */
  --background, --foreground
  --card, --card-foreground
  --popover, --popover-foreground
  --primary, --primary-foreground
  --secondary, --secondary-foreground
  --muted, --muted-foreground
  --accent, --accent-foreground
  --destructive, --destructive-foreground
  --border, --input, --ring
  --chart-1 hasta --chart-5
  ```

**Archivos afectados**:
- `frontend/app/globals.css` (eliminar líneas 3-23, 30-100)
- `frontend/components/Sidebar.tsx` (líneas 60-155)
- `frontend/app/strategies/page.tsx` (si usa custom colors)

**Resultado esperado**:
- ✅ Dark mode funcionando en TODOS los componentes
- ✅ Un solo sistema de verdad
- ✅ Mantenimiento simplificado

---

#### 1.2 Fix Sidebar - 100% Adaptativo
**Objetivo**: Eliminar TODOS los colores hardcoded del Sidebar

**Cambios necesarios**:
```tsx
// ❌ ANTES (línea 80-82)
className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
  isActive
    ? 'bg-[#f3f4f6] text-[#111827] font-medium'
    : 'text-[#6b7280] hover:bg-[#f9fafb] hover:text-[#111827]'
}`}

// ✅ DESPUÉS
className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
  isActive
    ? 'bg-accent text-accent-foreground font-medium'
    : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
}`}
```

**Status icons** (líneas 60-69):
```tsx
// ❌ ANTES
case 'running':
  return <span className="w-2 h-2 rounded-full bg-[#10b981]" />;

// ✅ DESPUÉS
case 'running':
  return <span className="w-2 h-2 rounded-full bg-green-500 dark:bg-green-600" />;
```

**Archivos**:
- `frontend/components/Sidebar.tsx`

---

#### 1.3 Sistema de Tipografía Premium
**Objetivo**: Jerarquía visual clara tipo Railway

**Crear nuevas clases en globals.css**:
```css
/* Typography System - Railway/Vercel style */
.text-h1 {
  @apply text-4xl font-semibold tracking-tight text-foreground;
  letter-spacing: -0.03em;
}

.text-h2 {
  @apply text-3xl font-semibold tracking-tight text-foreground;
  letter-spacing: -0.02em;
}

.text-h3 {
  @apply text-2xl font-semibold tracking-tight text-foreground;
  letter-spacing: -0.015em;
}

.text-body-lg {
  @apply text-base text-foreground;
  letter-spacing: -0.011em;
}

.text-body {
  @apply text-sm text-foreground;
  letter-spacing: -0.006em;
}

.text-caption {
  @apply text-xs text-muted-foreground;
}

.text-label {
  @apply text-sm font-medium text-foreground;
}
```

**Aplicar consistentemente**:
- Dashboard headers → `.text-h2`
- Card titles → `.text-h3`
- Body text → `.text-body`
- Hints/labels → `.text-caption`

**Archivos**:
- `frontend/app/globals.css`
- Todas las páginas de dashboard
- Componentes Card con títulos

---

#### 1.4 Spacing Scale Estricto
**Objetivo**: Consistencia visual perfecta

**Regla**: Usar SOLO estos valores de padding/margin/gap:
```
4px  → p-1 / m-1 / gap-1
8px  → p-2 / m-2 / gap-2
12px → p-3 / m-3 / gap-3
16px → p-4 / m-4 / gap-4
24px → p-6 / m-6 / gap-6
32px → p-8 / m-8 / gap-8
48px → p-12 / m-12 / gap-12
64px → p-16 / m-16 / gap-16
```

**Estandarización**:
- **Cards**: `p-6` (24px) siempre
- **Page containers**: `p-8` (32px) siempre
- **Sections**: `gap-6` o `gap-8`
- **Form fields**: `gap-4`
- **List items**: `gap-3`

**Auditoría y fix**:
- [ ] Dashboard Capital
- [ ] Dashboard Operations
- [ ] Strategies page
- [ ] Builder pages
- [ ] LiveControl

---

#### 1.5 Breadcrumbs en Navegación Anidada
**Objetivo**: Usuario siempre sabe dónde está

**Implementar Breadcrumb component** (ya existe en shadcn/ui):
```tsx
// Ejemplo en /strategies/[id]/builder
<Breadcrumb>
  <BreadcrumbList>
    <BreadcrumbItem>
      <BreadcrumbLink href="/strategies">Strategies</BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbLink href={`/strategies/${id}`}>
        {strategyName}
      </BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbPage>Builder</BreadcrumbPage>
    </BreadcrumbItem>
  </BreadcrumbList>
</Breadcrumb>
```

**Añadir a**:
- [ ] `/strategies/[id]/*` (todas las sub-rutas)
- [ ] `/dashboard/*`
- [ ] Builder, LiveControl, Analysis pages

**Posición**: Top de la página, antes del header principal

---

### **FASE 2: PREMIUM FEATURES** (3-4 días)
*Añadir features que definen UX premium tipo Railway/Vercel*

#### 2.1 Command Palette (Cmd+K) ⭐ MUST-HAVE
**Objetivo**: Navegación ultra-rápida tipo Railway

**Librería**: `cmdk` (by Paco Coursey - mismo de Vercel)

**Instalación**:
```bash
npm install cmdk
```

**Features**:
- **Cmd+K** para abrir (Mac) / **Ctrl+K** (Windows/Linux)
- **Search** across:
  - Navegación (Dashboard, Strategies, Markets, Settings)
  - Actions (Create Strategy, Run Backtest, Export Data)
  - Strategies activas (quick access a /strategies/[id])
  - Theme switching
  - Recent pages
- **Keyboard shortcuts**:
  - `↑↓` navegar
  - `Enter` ejecutar
  - `Esc` cerrar
- **Groups**:
  - Navigation
  - Actions
  - Strategies
  - Settings
  - Theme

**Diseño**:
```tsx
// Estilo Railway/Vercel
<CommandDialog open={open} onOpenChange={setOpen}>
  <CommandInput placeholder="Type a command or search..." />
  <CommandList>
    <CommandEmpty>No results found.</CommandEmpty>

    <CommandGroup heading="Navigation">
      <CommandItem onSelect={() => router.push('/dashboard/capital')}>
        <LineChart className="mr-2 h-4 w-4" />
        <span>Capital Dashboard</span>
        <CommandShortcut>⌘C</CommandShortcut>
      </CommandItem>
      {/* ... más items */}
    </CommandGroup>

    <CommandGroup heading="Actions">
      <CommandItem onSelect={createStrategy}>
        <Plus className="mr-2 h-4 w-4" />
        <span>Create Strategy</span>
        <CommandShortcut>⌘N</CommandShortcut>
      </CommandItem>
    </CommandGroup>

    <CommandSeparator />

    <CommandGroup heading="Theme">
      <CommandItem onSelect={() => setTheme("light")}>
        <Sun className="mr-2 h-4 w-4" />
        <span>Light</span>
      </CommandItem>
      <CommandItem onSelect={() => setTheme("dark")}>
        <Sun className="mr-2 h-4 w-4" />
        <span>Dark</span>
      </CommandItem>
    </CommandGroup>
  </CommandList>
</CommandDialog>
```

**Integración**:
- Crear `frontend/components/CommandPalette.tsx`
- Añadir a Layout.tsx
- Documentar shortcuts en `/settings`

**Resultado**:
- ✅ Navegación lightning-fast
- ✅ UX power-user
- ✅ Look & feel premium

---

#### 2.2 Empty States de Lujo
**Objetivo**: Guiar al usuario cuando no hay datos

**Componente reutilizable**:
```tsx
// components/EmptyState.tsx
interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <Card className="flex flex-col items-center justify-center p-12 text-center">
      <div className="rounded-full bg-muted p-3 mb-4">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-h3 mb-2">{title}</h3>
      <p className="text-body text-muted-foreground mb-6 max-w-sm">
        {description}
      </p>
      {action && (
        <Button onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </Card>
  );
}
```

**Implementar en**:
- [ ] Strategies page (cuando no hay estrategias)
- [ ] Capital page (cuando no hay capital asignado)
- [ ] Operations page (cuando no hay alertas)
- [ ] Decision Traces (cuando no hay traces)
- [ ] Markets (cuando no hay mercados activos)

**Ejemplo**:
```tsx
// En strategies/page.tsx
{strategies.length === 0 && (
  <EmptyState
    icon={LineChart}
    title="No strategies yet"
    description="Create your first algorithmic trading strategy to get started with automated trading."
    action={{
      label: "Create Strategy",
      onClick: () => router.push('/strategies/new')
    }}
  />
)}
```

---

#### 2.3 Loading States Premium
**Objetivo**: Feedback visual instantáneo en TODAS las acciones

**Buttons con loading**:
```tsx
// Mejorar Button component para soportar loading
<Button loading={isSubmitting}>
  {isSubmitting ? (
    <>
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      Creating...
    </>
  ) : (
    'Create Strategy'
  )}
</Button>
```

**Skeleton loading**: Ya implementado ✅
- Mantener uso en data-heavy pages

**Progress indicators** para operaciones largas:
```tsx
// Para backtest, optimization, etc.
<Progress value={progress} className="mb-2" />
<p className="text-caption">Processing {progress}%...</p>
```

**Optimistic updates**:
- Al crear estrategia: mostrar inmediatamente en lista (con badge "Creating...")
- Al pausar: cambiar estado inmediatamente
- Al eliminar: fade out inmediato

**Archivos**:
- [ ] Actualizar todos los formularios
- [ ] Strategy actions (pause, resume, delete)
- [ ] Settings pages
- [ ] File uploads

---

#### 2.4 Enhanced Error Handling
**Objetivo**: Errores informativos con recovery actions

**Error Banner Component**:
```tsx
// components/ErrorBanner.tsx
interface ErrorBannerProps {
  error: Error | string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ErrorBanner({ error, onRetry, onDismiss }: ErrorBannerProps) {
  const message = typeof error === 'string' ? error : error.message;

  return (
    <Alert variant="destructive" className="mb-6">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Something went wrong</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span>{message}</span>
        <div className="flex gap-2 ml-4">
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          )}
          {onDismiss && (
            <Button variant="ghost" size="sm" onClick={onDismiss}>
              Dismiss
            </Button>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}
```

**Error categories**:
- **Network errors**: Show retry button
- **Auth errors**: Redirect to login
- **Validation errors**: Inline en formularios
- **Server errors**: Show contact support link

**Implementar**:
- [ ] Dashboard data fetching
- [ ] Strategy CRUD operations
- [ ] API calls en LiveControl
- [ ] File uploads

---

#### 2.5 Microinteracciones Suaves
**Objetivo**: App se siente fluida y responsive

**Page transitions** con Framer Motion:
```tsx
// app/layout.tsx o page wrapper
import { motion } from 'framer-motion';

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 }
};

export default function PageWrapper({ children }) {
  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={pageVariants}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}
```

**Hover states mejorados**:
```tsx
// Cards interactivas
<Card className="transition-all hover:shadow-md hover:border-primary/50">
  {/* contenido */}
</Card>

// Nav items (ya están en Sidebar, revisar)
<Link className="transition-colors hover:text-primary">
  {/* ... */}
</Link>
```

**Animaciones discretas**:
- Badges de estado con `animate-pulse` sutil
- Números que cambian con CountUp animation
- Gráficas con entrada animada (Recharts ya lo soporta)

**Focus states visibles**:
```css
/* globals.css */
*:focus-visible {
  @apply outline-none ring-2 ring-primary ring-offset-2 ring-offset-background;
}
```

---

#### 2.6 Search & Filter Premium
**Objetivo**: Encontrar info rápidamente

**Strategies page**:
```tsx
// Filtros múltiples
<div className="flex gap-3 mb-6">
  <div className="relative flex-1">
    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
    <Input
      placeholder="Search strategies..."
      value={search}
      onChange={(e) => setSearch(e.target.value)}
      className="pl-9"
    />
  </div>

  <Select value={statusFilter} onValueChange={setStatusFilter}>
    <SelectTrigger className="w-[180px]">
      <SelectValue placeholder="Status" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="all">All</SelectItem>
      <SelectItem value="running">Running</SelectItem>
      <SelectItem value="paused">Paused</SelectItem>
      <SelectItem value="error">Error</SelectItem>
    </SelectContent>
  </Select>

  <Select value={typeFilter} onValueChange={setTypeFilter}>
    <SelectTrigger className="w-[180px]">
      <SelectValue placeholder="Type" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="all">All Types</SelectItem>
      <SelectItem value="surebet">Surebet</SelectItem>
      <SelectItem value="arbitrage">Arbitrage</SelectItem>
      <SelectItem value="market_making">Market Making</SelectItem>
    </SelectContent>
  </Select>
</div>
```

**Capital page - Filter by strategy**:
```tsx
<Tabs defaultValue="all">
  <TabsList>
    <TabsTrigger value="all">All Strategies</TabsTrigger>
    <TabsTrigger value="surebet">Surebet</TabsTrigger>
    <TabsTrigger value="arbitrage">Arbitrage</TabsTrigger>
  </TabsList>
</Tabs>
```

**Operations page - Time range selector**:
```tsx
<Select value={timeRange} onValueChange={setTimeRange}>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Time range" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="1h">Last hour</SelectItem>
    <SelectItem value="6h">Last 6 hours</SelectItem>
    <SelectItem value="24h">Last 24 hours</SelectItem>
    <SelectItem value="7d">Last 7 days</SelectItem>
  </SelectContent>
</Select>
```

---

### **FASE 3: POLISH & REFINEMENT** (2-3 días)
*Detalles que separan "bueno" de "excepcional"*

#### 3.1 CSS Ultra-Premium
**Objetivo**: Visual polish tipo Railway

**Elevaciones sutiles**:
```css
/* globals.css - Actualizar shadow system */
.shadow-sm {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.shadow {
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1),
              0 1px 2px -1px rgba(0, 0, 0, 0.1);
}

.shadow-md {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
              0 2px 4px -2px rgba(0, 0, 0, 0.1);
}

/* Dark mode shadows */
.dark .shadow-md {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3),
              0 2px 4px -2px rgba(0, 0, 0, 0.2);
}
```

**Border radius consistente**:
```css
/* Usar SOLO estos valores */
rounded-sm  → 4px   (badges, tags)
rounded-md  → 6px   (buttons, inputs)
rounded-lg  → 8px   (cards)
rounded-xl  → 12px  (modals, popovers)
rounded-2xl → 16px  (hero elements)
```

**Gradients sutiles** (solo para hero sections):
```tsx
// Hero gradient tipo Railway
<div className="bg-gradient-to-br from-background via-background to-muted/20">
  {/* content */}
</div>
```

**Glass morphism** (opcional, para modals):
```css
.glass {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.dark .glass {
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

---

#### 3.2 Improved Charts UX
**Objetivo**: Gráficas más informativas

**Time range selector en todas las gráficas**:
```tsx
<Card>
  <CardHeader className="flex flex-row items-center justify-between">
    <CardTitle>Equity Curve</CardTitle>
    <Select value={range} onValueChange={setRange}>
      <SelectTrigger className="w-[120px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="1h">1 hour</SelectItem>
        <SelectItem value="1d">1 day</SelectItem>
        <SelectItem value="7d">7 days</SelectItem>
        <SelectItem value="30d">30 days</SelectItem>
        <SelectItem value="all">All time</SelectItem>
      </SelectContent>
    </Select>
  </CardHeader>
  <CardContent>
    {/* chart */}
  </CardContent>
</Card>
```

**Summary stats encima de cada gráfica**:
```tsx
// Antes de la gráfica
<div className="grid grid-cols-3 gap-4 mb-4">
  <div>
    <p className="text-caption">Current</p>
    <p className="text-h3">${currentValue.toLocaleString()}</p>
  </div>
  <div>
    <p className="text-caption">Change (24h)</p>
    <p className={cn(
      "text-h3",
      change24h >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
    )}>
      {change24h >= 0 ? '+' : ''}{change24h.toFixed(2)}%
    </p>
  </div>
  <div>
    <p className="text-caption">Peak</p>
    <p className="text-h3">${peakValue.toLocaleString()}</p>
  </div>
</div>
```

**Tooltips mejorados**:
```tsx
// Custom tooltip para Recharts
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null;

  return (
    <Card className="p-3 shadow-lg border-border/50">
      <p className="text-caption mb-1">{label}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-body font-medium">
            {entry.name}: ${entry.value.toLocaleString()}
          </span>
        </div>
      ))}
    </Card>
  );
};
```

**Actualizar todas las gráficas**:
- [ ] Dashboard Capital (2 charts)
- [ ] Dashboard Operations (2 charts)
- [ ] LiveControl (3 charts)

---

#### 3.3 Accessibility Audit
**Objetivo**: WCAG AA compliance

**Checklist**:
- [ ] **Keyboard navigation**: Todas las acciones accesibles con Tab
- [ ] **Focus indicators**: Visibles en todos los elementos interactivos
- [ ] **aria-labels**: Añadir a iconos sin texto
- [ ] **Contrast ratio**: Verificar con herramienta (min 4.5:1 para texto)
- [ ] **Screen reader**: Probar con VoiceOver/NVDA
- [ ] **Skip links**: Añadir "Skip to main content"
- [ ] **Form validation**: Mensajes de error accesibles
- [ ] **Alt text**: Imágenes/gráficas con descripción

**Herramientas**:
- Lighthouse (Chrome DevTools)
- axe DevTools (extensión)
- WAVE (web accessibility evaluation tool)

**Implementar**:
```tsx
// Skip link (añadir en Layout)
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md"
>
  Skip to main content
</a>

// Main content
<main id="main-content">
  {children}
</main>
```

---

#### 3.4 Performance Optimization
**Objetivo**: App lightning-fast

**Tareas**:
- [ ] **Code splitting**: Lazy load heavy components
  ```tsx
  const StrategyBuilder = dynamic(() => import('@/components/strategy/builder'), {
    loading: () => <ChartSkeleton />,
    ssr: false
  });
  ```

- [ ] **Image optimization**: Usar Next.js Image component
  ```tsx
  import Image from 'next/image';
  <Image src="/logo.png" width={120} height={40} alt="AlphaEdge" />
  ```

- [ ] **Memoization**: React.memo en componentes pesados
  ```tsx
  export const StrategyNode = React.memo(({ data, id }) => {
    // ...
  });
  ```

- [ ] **Virtual scrolling**: Para listas largas (react-window)
  ```tsx
  import { FixedSizeList } from 'react-window';

  <FixedSizeList
    height={600}
    itemCount={strategies.length}
    itemSize={80}
  >
    {StrategyRow}
  </FixedSizeList>
  ```

- [ ] **Debounce search**: Evitar requests excesivos
  ```tsx
  const debouncedSearch = useMemo(
    () => debounce((value: string) => {
      fetchStrategies(value);
    }, 300),
    []
  );
  ```

- [ ] **Optimistic updates**: Actualizar UI antes de response

**Métricas objetivo**:
- First Contentful Paint (FCP): < 1.8s
- Largest Contentful Paint (LCP): < 2.5s
- Time to Interactive (TTI): < 3.5s
- Cumulative Layout Shift (CLS): < 0.1

---

#### 3.5 Storybook Setup
**Objetivo**: Design system documentado

**Instalación**:
```bash
npx storybook@latest init
```

**Componentes a documentar**:
- [ ] Todos los `components/ui/*` (shadcn/ui wrappers)
- [ ] EmptyState
- [ ] ErrorBanner
- [ ] LoadingSpinner
- [ ] Skeletons (Table, Chart, Dashboard)
- [ ] MetricsPanel
- [ ] StrategyNode

**Template**:
```tsx
// components/EmptyState.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { EmptyState } from './EmptyState';
import { LineChart } from 'lucide-react';

const meta: Meta<typeof EmptyState> = {
  title: 'Components/EmptyState',
  component: EmptyState,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof EmptyState>;

export const Default: Story = {
  args: {
    icon: LineChart,
    title: 'No strategies yet',
    description: 'Create your first strategy to get started.',
    action: {
      label: 'Create Strategy',
      onClick: () => console.log('Create clicked'),
    },
  },
};

export const WithoutAction: Story = {
  args: {
    icon: LineChart,
    title: 'No data available',
    description: 'There is no data to display at the moment.',
  },
};
```

**Añadir visual regression**:
```bash
npm install --save-dev @storybook/addon-chromatic
```

---

### **FASE 4: EXTRAS PREMIUM** (2-3 días - OPCIONAL)
*Features avanzadas que elevan la experiencia*

#### 4.1 Keyboard Shortcuts Overlay
**Objetivo**: Mostrar shortcuts disponibles con `?`

**Componente**:
```tsx
// components/KeyboardShortcutsDialog.tsx
const shortcuts = [
  { key: '⌘K', description: 'Open command palette' },
  { key: '⌘N', description: 'Create new strategy' },
  { key: '⌘C', description: 'Go to Capital Dashboard' },
  { key: '⌘O', description: 'Go to Operations Dashboard' },
  { key: '⌘/', description: 'Toggle sidebar' },
  { key: '?', description: 'Show shortcuts' },
  { key: 'Esc', description: 'Close dialog/modal' },
];

export function KeyboardShortcutsDialog({ open, onClose }) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          {shortcuts.map((shortcut) => (
            <div key={shortcut.key} className="flex justify-between items-center">
              <span className="text-body">{shortcut.description}</span>
              <kbd className="px-2 py-1 bg-muted text-muted-foreground rounded text-xs font-mono">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

**Trigger**: Presionar `?` abre el dialog

---

#### 4.2 Customizable Dashboard
**Objetivo**: Usuario puede reorganizar widgets

**Librería**: `react-grid-layout`

```tsx
import GridLayout from 'react-grid-layout';

const layout = [
  { i: 'equity', x: 0, y: 0, w: 6, h: 4 },
  { i: 'pnl', x: 6, y: 0, w: 6, h: 4 },
  { i: 'alerts', x: 0, y: 4, w: 12, h: 3 },
];

<GridLayout
  layout={layout}
  cols={12}
  rowHeight={60}
  width={1200}
  onLayoutChange={saveLayout}
>
  <Card key="equity">{/* Equity widget */}</Card>
  <Card key="pnl">{/* PnL widget */}</Card>
  <Card key="alerts">{/* Alerts widget */}</Card>
</GridLayout>
```

**Features**:
- Drag & drop widgets
- Resize widgets
- Reset to default layout
- Save layout preferences (localStorage o backend)

---

#### 4.3 Tour/Onboarding Flow
**Objetivo**: Nuevos usuarios aprenden rápido

**Librería**: `react-joyride`

```tsx
import Joyride from 'react-joyride';

const steps = [
  {
    target: '.sidebar',
    content: 'Navigate between sections using the sidebar.',
  },
  {
    target: '.command-palette-trigger',
    content: 'Press ⌘K to quickly access any feature.',
  },
  {
    target: '.create-strategy-btn',
    content: 'Create your first strategy here.',
  },
];

<Joyride
  steps={steps}
  continuous
  showProgress
  showSkipButton
  styles={{
    options: {
      primaryColor: 'hsl(var(--primary))',
    },
  }}
/>
```

**Trigger**: Primera visita o desde Settings

---

#### 4.4 Advanced Analytics Dashboard
**Objetivo**: Insights profundos del rendimiento

**Widgets adicionales**:
- **Sharpe Ratio evolution** (LineChart)
- **Max Drawdown timeline** (AreaChart con annotations)
- **Win/Loss ratio** (Donut chart)
- **Strategy correlation matrix** (Heatmap)
- **Monthly returns table** (Table con color coding)
- **Risk-adjusted returns** (Scatter plot)

**Features**:
- Comparar múltiples estrategias
- Export data (CSV, JSON)
- Custom date ranges
- Benchmark comparison (S&P 500, BTC, etc.)

---

#### 4.5 Real-time Notifications
**Objetivo**: Alertas instant en la app

**Implementación**:
```tsx
// Usar sonner (ya instalado)
import { toast } from 'sonner';

// Conectar WebSocket o Server-Sent Events
useEffect(() => {
  const eventSource = new EventSource('/api/notifications/stream');

  eventSource.addEventListener('alert', (event) => {
    const alert = JSON.parse(event.data);

    toast.error(alert.message, {
      description: alert.details,
      action: {
        label: 'View',
        onClick: () => router.push(`/strategies/${alert.strategy_id}`),
      },
    });
  });

  return () => eventSource.close();
}, []);
```

**Tipos de notificaciones**:
- Strategy errors
- Risk threshold exceeded
- Large P&L changes
- API health issues
- New market opportunities

**Preferencias**:
- User puede silenciar por estrategia
- Configurar severidad mínima
- Do Not Disturb mode

---

## 📋 Resumen Ejecutivo

### Prioridades por Impacto

#### 🔴 CRÍTICO (Hacer YA)
1. **Consolidar sistema de color** (FASE 1.1)
2. **Fix Sidebar hardcoded colors** (FASE 1.2)
3. **Breadcrumbs** (FASE 1.5)

#### 🟡 ALTO IMPACTO (Esta semana)
4. **Command Palette** (FASE 2.1)
5. **Empty States** (FASE 2.2)
6. **Tipografía consistente** (FASE 1.3)
7. **Spacing estandarizado** (FASE 1.4)

#### 🟢 MEDIUM IMPACTO (Próximas 2 semanas)
8. **Loading states mejorados** (FASE 2.3)
9. **Error handling premium** (FASE 2.4)
10. **Search & Filter** (FASE 2.6)
11. **Microinteracciones** (FASE 2.5)

#### 🔵 POLISH (Cuando haya tiempo)
12. **CSS ultra-premium** (FASE 3.1)
13. **Charts UX** (FASE 3.2)
14. **Accessibility audit** (FASE 3.3)
15. **Performance optimization** (FASE 3.4)
16. **Storybook** (FASE 3.5)

#### ⭐ EXTRAS (Opcional)
17. **Keyboard shortcuts overlay** (FASE 4.1)
18. **Customizable dashboard** (FASE 4.2)
19. **Tour/onboarding** (FASE 4.3)
20. **Advanced analytics** (FASE 4.4)
21. **Real-time notifications** (FASE 4.5)

---

## 🎯 Objetivos Medibles

### Antes → Después

| Métrica | Actual | Meta | Delta |
|---------|--------|------|-------|
| shadcn/ui coverage | 100% ✅ | 100% | - |
| Dark mode funcional | 90% ⚠️ | 100% ✅ | +10% |
| Hardcoded colors | ~15 ❌ | 0 ✅ | -100% |
| Sistema de color | 2 conflictivos ❌ | 1 unificado ✅ | -50% |
| Breadcrumbs | 0% | 100% | +100% |
| Command palette | No ❌ | Sí ✅ | - |
| Empty states | Básicos | Premium | - |
| Loading UX | 7/10 | 10/10 | +30% |
| Error recovery | Básico | Premium | - |
| Lighthouse Score | ~75 | 95+ | +20pts |
| Accessibility | ~70 | 95+ (WCAG AA) | +25pts |
| First Load (s) | ~2.5 | <1.8 | -28% |

---

## 📁 Archivos a Modificar

### FASE 1 (Fundación)
```
✏️ frontend/app/globals.css (consolidar tokens, tipografía)
✏️ frontend/components/Sidebar.tsx (eliminar hardcoded)
✏️ frontend/app/dashboard/capital/page.tsx (breadcrumbs, spacing)
✏️ frontend/app/dashboard/operations/page.tsx (breadcrumbs, spacing)
✏️ frontend/app/strategies/page.tsx (breadcrumbs, spacing)
✏️ frontend/app/strategies/[id]/*/page.tsx (breadcrumbs)
```

### FASE 2 (Premium Features)
```
🆕 frontend/components/CommandPalette.tsx
🆕 frontend/components/EmptyState.tsx
🆕 frontend/components/ErrorBanner.tsx
✏️ frontend/components/Layout.tsx (integrar CommandPalette)
✏️ frontend/components/ui/button.tsx (añadir loading prop)
✏️ Todas las páginas (añadir empty states, error handling)
```

### FASE 3 (Polish)
```
✏️ frontend/app/globals.css (shadows, focus states)
✏️ Todas las páginas con charts (time range, tooltips)
🆕 frontend/.storybook/* (setup)
🆕 frontend/components/**/*.stories.tsx
```

### FASE 4 (Extras)
```
🆕 frontend/components/KeyboardShortcutsDialog.tsx
🆕 frontend/components/CustomizableDashboard.tsx
🆕 frontend/components/OnboardingTour.tsx
🆕 frontend/app/dashboard/analytics/page.tsx
```

---

## ⏱️ Estimación de Tiempo

| Fase | Días | Descripción |
|------|------|-------------|
| **FASE 1** | 2-3 | Fundación sólida |
| **FASE 2** | 3-4 | Premium features |
| **FASE 3** | 2-3 | Polish & refinement |
| **FASE 4** | 2-3 | Extras (opcional) |
| **TOTAL** | **9-13 días** | Para UX ultra-premium |

**TOTAL sin extras**: 7-10 días para nivel Railway/Vercel

---

## 🚀 Siguientes Pasos Inmediatos

### Para empezar HOY:

1. **Crear branch**:
   ```bash
   git checkout -b ux-premium-transformation
   ```

2. **FASE 1.1 - Sistema de color**:
   - Abrir `frontend/app/globals.css`
   - Eliminar líneas 3-23 (custom @theme variables)
   - Eliminar líneas 80-100 (custom card/input styles)
   - Conservar SOLO shadcn/ui tokens y chart variables

3. **FASE 1.2 - Fix Sidebar**:
   - Abrir `frontend/components/Sidebar.tsx`
   - Reemplazar ALL hardcoded colors:
     - `bg-[#f3f4f6]` → `bg-accent`
     - `text-[#111827]` → `text-accent-foreground`
     - `text-[#6b7280]` → `text-muted-foreground`
     - `hover:bg-[#f9fafb]` → `hover:bg-accent/50`

4. **Test dark mode**:
   - Abrir app en navegador
   - Toggle entre light/dark/black
   - Verificar que TODO funciona

5. **Commit**:
   ```bash
   git add .
   git commit -m "feat(ux): consolidate color system and fix Sidebar dark mode"
   ```

---

## 🎨 Referencias de Diseño

### Inspiración Railway
- **Color palette**: Minimalista, mucho uso de grises sutiles
- **Typography**: Inter variable, tracking tight en headings
- **Spacing**: Generoso, mucho aire
- **Cards**: Bordes sutiles, sombras mínimas
- **Hover states**: Cambio de background, NO de border
- **Command palette**: Central, potente, keyboard-first

### Inspiración Vercel
- **Black mode**: OLED-friendly, negro puro
- **Gradients**: Muy sutiles, solo en heroes
- **Microinteracciones**: Suaves, 200ms duration
- **Empty states**: Ilustraciones SVG custom
- **Loading**: Skeleton con shimmer effect
- **Charts**: Minimalistas, focus en datos

### Design Tokens Recomendados
```css
/* Spacing scale (8px base) */
4, 8, 12, 16, 24, 32, 48, 64, 96, 128

/* Border radius */
4, 6, 8, 12, 16

/* Font sizes */
12, 14, 16, 18, 20, 24, 30, 36, 48

/* Font weights */
400 (normal), 500 (medium), 600 (semibold)

/* Line heights */
1.2 (tight - headings)
1.5 (normal - body)
1.75 (relaxed - long form)

/* Letter spacing */
-0.03em (display)
-0.02em (h1-h2)
-0.015em (h3)
-0.011em (body)
0 (caption)
```

---

## ✅ Checklist de Calidad Final

Antes de considerar el proyecto "ultra-premium":

### Diseño
- [ ] Un solo sistema de color (shadcn/ui tokens)
- [ ] Tipografía 100% consistente
- [ ] Spacing siguiendo escala estricta (4-8-12-16-24-32-48-64)
- [ ] Border radius consistente
- [ ] Shadows sutiles y coherentes

### Funcionalidad
- [ ] Command palette funcionando (Cmd+K)
- [ ] Breadcrumbs en todas las rutas anidadas
- [ ] Empty states informativos con CTAs
- [ ] Error handling con recovery actions
- [ ] Loading states en TODAS las acciones async
- [ ] Search & filter en listas largas

### Dark Mode
- [ ] Light mode perfecto
- [ ] Dark mode perfecto
- [ ] Black mode (OLED) perfecto
- [ ] System preference funciona
- [ ] CERO colores hardcoded
- [ ] CERO elementos rotos visualmente

### Performance
- [ ] Lighthouse Score > 95
- [ ] FCP < 1.8s
- [ ] LCP < 2.5s
- [ ] CLS < 0.1
- [ ] TTI < 3.5s

### Accesibilidad
- [ ] Keyboard navigation completa
- [ ] Focus indicators visibles
- [ ] aria-labels donde necesarios
- [ ] Contrast ratio WCAG AA
- [ ] Screen reader compatible
- [ ] Skip links implementados

### UX
- [ ] Transiciones suaves (200ms)
- [ ] Hover states en elementos interactivos
- [ ] Optimistic updates donde apropiado
- [ ] Toast notifications coherentes
- [ ] No CLS (layout shifts)

### Documentación
- [ ] Storybook con componentes principales
- [ ] README actualizado
- [ ] Design system documentado
- [ ] Keyboard shortcuts listados

---

## 🎓 Aprendizajes y Mejores Prácticas

### DO ✅
1. **Usar UN solo sistema de tokens** (shadcn/ui)
2. **Testear en los 4 modos de tema** siempre
3. **Aplicar spacing scale estricto** (no valores random)
4. **Componentes accesibles** desde el inicio
5. **Skeleton > Spinner** para loading
6. **Empty states** siempre con CTAs
7. **Error recovery** en lugar de solo mostrar error
8. **Optimistic updates** para mejor UX
9. **Keyboard-first**: Command palette, shortcuts
10. **Microinteracciones sutiles** (200ms, ease-out)

### DON'T ❌
1. **NO hardcodear colores** NUNCA (usar tokens)
2. **NO crear custom variants** si shadcn/ui tiene
3. **NO usar spacing random** (stick to scale)
4. **NO ignorar dark mode** en ningún componente
5. **NO spinners genéricos** (usar skeletons)
6. **NO alerts() nativos** (usar toast)
7. **NO forms sin validación inline**
8. **NO acciones sin loading state**
9. **NO listas largas sin virtual scroll**
10. **NO deploy sin Lighthouse check**

---

## 📞 Siguiente Acción

**¿Quieres que empiece con la implementación?**

Puedo empezar por:
1. **FASE 1.1 + 1.2** (Sistema de color + Fix Sidebar) ← RECOMENDADO
2. **Solo revisar el plan** y hacer ajustes
3. **Otra prioridad específica** que quieras atacar primero

Confirma y arrancamos 🚀
