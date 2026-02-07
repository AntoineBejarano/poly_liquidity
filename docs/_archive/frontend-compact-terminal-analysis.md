# Análisis Frontend: Transformación a Terminal Compacto Premium

**Objetivo**: Reutilizar frontend existente y transformarlo a diseño compacto tipo trading terminal, sin colorines, premium y herramienta top.

**Fecha**: 2025-01-XX

---

## 📊 Estado Actual del Frontend

### ✅ Lo que YA tenemos y podemos REUTILIZAR

#### 1. **Infraestructura Base** (100% reutilizable)
- ✅ **Next.js 14 App Router** - Estructura sólida
- ✅ **shadcn/ui** - Componentes base (Button, Card, Input, Table, etc.)
- ✅ **Tailwind CSS** - Configurado con design tokens
- ✅ **TypeScript** - Type-safety completo
- ✅ **Layout + Sidebar** - Estructura base funcional
- ✅ **CommandPalette** - Ya existe (reutilizar)
- ✅ **ThemeToggle** - Dark mode funcional
- ✅ **Skeleton loading** - Ya implementado

#### 2. **Design Tokens** (necesitan ajustes menores)
- ✅ **Variables CSS** - Sistema de colores con `--background`, `--foreground`, etc.
- ✅ **Tipografía** - Clases `.text-h1`, `.text-h2`, `.text-body`, etc.
- ✅ **Spacing** - Sistema base (necesita compactarse)
- ✅ **Shadows** - `.shadow-premium-sm`, `.shadow-premium`, etc.

#### 3. **Componentes UI Base** (reutilizables con ajustes)
- ✅ `Button` - Necesita variante compacta (`h-8`, `h-7`)
- ✅ `Card` - Necesita padding reducido (`p-3` en lugar de `p-6`)
- ✅ `Input` - Necesita altura reducida (`h-8` en lugar de `h-10`)
- ✅ `Table` - Necesita row height reducido (`h-9` en lugar de `h-12`)
- ✅ `Badge` - Reutilizable tal cual
- ✅ `Select`, `Dropdown` - Reutilizables

#### 4. **Páginas Existentes** (estructura reutilizable)
- ✅ `/markets` - Estructura OK, necesita compactarse
- ✅ `/strategies/[id]/live` - Estructura OK, necesita reorganización
- ✅ `/strategies/new` - Necesita rebuild compacto
- ✅ Layout base - Reutilizable

#### 5. **Hooks y Utilidades** (100% reutilizables)
- ✅ `useBackendConnection` - OK
- ✅ `useComponentDataLoader` - OK
- ✅ `useRealtimeStrategy` - OK
- ✅ `lib/api.ts` - OK

---

## 🎯 Cambios Necesarios para Terminal Compacto

### **FASE 1: Design Tokens Compactos** (1 día)

#### 1.1 Ajustar Tipografía a Compacta

**Archivo**: `frontend/app/globals.css`

**Cambios**:
```css
/* ANTES (actual) */
.text-h1 {
  font-size: 2.25rem;  /* 36px - muy grande */
  line-height: 2.5rem;
}

.text-body {
  font-size: 0.875rem;  /* 14px */
  line-height: 1.25rem;
}

/* DESPUÉS (compacto) */
.text-h1 {
  font-size: 1rem;      /* 16px - compacto */
  line-height: 1.25rem; /* 20px */
  font-weight: 600;
}

.text-h2 {
  font-size: 0.875rem;  /* 14px */
  line-height: 1.125rem; /* 18px */
  font-weight: 600;
}

.text-h3 {
  font-size: 0.8125rem; /* 13px */
  line-height: 1rem;    /* 16px */
  font-weight: 600;
}

.text-body {
  font-size: 0.8125rem; /* 13px - base */
  line-height: 1.25rem;  /* 20px */
}

.text-caption {
  font-size: 0.75rem;   /* 12px */
  line-height: 1rem;    /* 16px */
}
```

#### 1.2 Ajustar Spacing a Compacto

**Cambios en `globals.css`**:
```css
/* Añadir utilidades compactas */
.spacing-compact {
  --spacing-xs: 0.25rem;  /* 4px */
  --spacing-sm: 0.5rem;   /* 8px */
  --spacing-md: 0.75rem;  /* 12px */
  --spacing-lg: 1rem;     /* 16px */
  --spacing-xl: 1.5rem;   /* 24px */
}

/* Reemplazar p-6 por p-3 en cards */
.card-compact {
  padding: 0.75rem; /* p-3 */
}
```

#### 1.3 Ajustar Componentes Base

**Archivo**: `frontend/components/ui/button.tsx`

**Añadir variante compacta**:
```tsx
const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: { /* ... igual ... */ },
      size: {
        default: "h-10 px-4 py-2",  // Mantener para compatibilidad
        sm: "h-9 rounded-md px-3",
        compact: "h-8 px-3 text-[13px]",      // ⭐ NUEVO
        compact-sm: "h-7 px-2 text-[13px]",    // ⭐ NUEVO
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
  }
)
```

**Archivo**: `frontend/components/ui/input.tsx`

**Cambios**:
```tsx
const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-8 w-full rounded-md border border-input bg-background px-3 py-1.5 text-[13px] ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
```

**Archivo**: `frontend/components/ui/card.tsx`

**Añadir variante compacta**:
```tsx
const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { compact?: boolean }>(
  ({ className, compact = false, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-xl border bg-card text-card-foreground shadow-sm", // rounded-xl en lugar de rounded-lg
        compact ? "p-3" : "p-6", // ⭐ Compact por defecto
        className
      )}
      {...props}
    />
  )
)
```

**Archivo**: `frontend/components/ui/table.tsx`

**Cambios**:
```tsx
const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <th
      ref={ref}
      className={cn(
        "h-9 px-3 text-left align-middle text-[13px] font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0", // h-9 en lugar de h-12, px-3 en lugar de px-4
        className
      )}
      {...props}
    />
  )
)

const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td
      ref={ref}
      className={cn("p-3 align-middle text-[13px] [&:has([role=checkbox])]:pr-0", className)} // p-3 en lugar de p-4
      {...props}
    />
  )
)

const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(
        "border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted h-9", // h-9 explícito
        className
      )}
      {...props}
    />
  )
)
```

---

### **FASE 2: Layout Compacto** (1 día)

#### 2.1 Ajustar Layout Principal

**Archivo**: `frontend/components/Layout.tsx`

**Cambios**:
```tsx
// ANTES
<main className="flex-1 overflow-y-auto">
  <div className="min-h-full p-6 max-w-[1920px] mx-auto w-full">
    <DynamicBreadcrumbs />
    {children}
  </div>
</main>

// DESPUÉS (compacto)
<main className="flex-1 overflow-y-auto">
  <div className="min-h-full px-3 py-2 max-w-[1920px] mx-auto w-full"> {/* px-3 py-2 en lugar de p-6 */}
    <DynamicBreadcrumbs />
    {children}
  </div>
</main>
```

#### 2.2 Ajustar Sidebar Compacto

**Archivo**: `frontend/components/Sidebar.tsx`

**Cambios**:
- Reducir padding: `p-4` → `p-3`
- Reducir gap: `gap-3` → `gap-2`
- Reducir font size: `text-sm` → `text-[13px]`
- Reducir padding items: `px-3 py-2` → `px-2 py-1.5`
- Mantener estructura, solo compactar

```tsx
// Ejemplo de cambio
const renderNavItem = (href: string, label: string, isActive: boolean) => {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-[13px] transition-colors ${
        isActive
          ? 'bg-accent text-accent-foreground font-medium'
          : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
      }`}
    >
      <span className="w-1 h-1 rounded-full bg-current opacity-60"></span>
      <span>{label}</span>
    </Link>
  );
};
```

#### 2.3 Topbar Compacto

**Archivo**: `frontend/components/Layout.tsx`

**Cambios**:
```tsx
// ANTES
<header className="h-14 border-b border-border bg-card flex items-center justify-end px-6 flex-shrink-0">

// DESPUÉS
<header className="h-10 border-b border-border bg-card flex items-center justify-between px-3 flex-shrink-0">
  {/* Añadir search y acciones primarias aquí */}
  <div className="flex items-center gap-2">
    {/* Search con / */}
    <Input 
      placeholder="Search /" 
      className="h-8 w-64 text-[13px]"
      onKeyDown={(e) => {
        if (e.key === '/') {
          // Focus search
        }
      }}
    />
  </div>
  <div className="flex items-center gap-2">
    {/* Play/Pause/Simulate/Stop buttons */}
    <ThemeToggle />
  </div>
</header>
```

---

### **FASE 3: Páginas Compactas** (2-3 días)

#### 3.1 `/markets` - Tabla Densa

**Archivo**: `frontend/app/markets/page.tsx`

**Cambios**:
- Eliminar cards grandes
- Tabla full-width con todas las columnas
- Filtros en línea (no dropdowns enormes)
- Panel lateral colapsable para detalles

**Estructura**:
```tsx
<div className="space-y-2"> {/* space-y-2 en lugar de space-y-6 */}
  {/* Topbar compacto */}
  <div className="flex items-center gap-2 px-3 py-2 border-b">
    <Input placeholder="Search /" className="h-8 flex-1" />
    <CategoriesFilter compact />
    <SeriesFilter compact />
    <TagsFilter compact />
  </div>
  
  {/* Tabla densa */}
  <Table>
    <TableHeader>
      <TableRow className="h-9">
        <TableHead className="px-3">Market</TableHead>
        <TableHead className="px-3">Status</TableHead>
        <TableHead className="px-3">YES Token</TableHead>
        <TableHead className="px-3">NO Token</TableHead>
        <TableHead className="px-3">Spread</TableHead>
        <TableHead className="px-3">Depth@50</TableHead>
        <TableHead className="px-3">Impact@1000</TableHead>
        <TableHead className="px-3">Actions</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {markets.map(market => (
        <TableRow key={market.id} className="h-9 hover:bg-muted/50">
          <TableCell className="px-3">{market.name}</TableCell>
          {/* ... más celdas ... */}
        </TableRow>
      ))}
    </TableBody>
  </Table>
</div>
```

#### 3.2 `/strategies/[id]/live` - Terminal Operacional

**Archivo**: `frontend/app/strategies/[id]/live/page.tsx`

**Cambios**:
- Topbar con status + capital + acciones
- Split 70/30: tabla izquierda + panel derecho
- Tabla densa con métricas de orderbook
- Panel derecho: health + precheck failures + recent orders

**Estructura**:
```tsx
<div className="flex flex-col h-full">
  {/* Topbar compacto */}
  <div className="flex items-center justify-between px-3 py-2 border-b bg-card">
    <div className="flex items-center gap-3">
      <StatusPill status={strategy.is_active ? 'active' : 'paused'} />
      <span className="text-[13px]">Capital: ${capitalUsed}/${maxCapital}</span>
      <span className="text-[13px]">Exposure: ${exposure}</span>
    </div>
    <div className="flex items-center gap-2">
      <Button size="compact" onClick={handleSimulate}>Simulate</Button>
      <Button size="compact" onClick={handlePlay}>Play</Button>
      <Button size="compact" onClick={handlePause}>Pause</Button>
      <Button size="compact-sm" variant="destructive" onClick={handleStop}>Stop</Button>
    </div>
  </div>
  
  {/* Main split */}
  <div className="flex flex-1 overflow-hidden">
    {/* Tabla izquierda (70%) */}
    <div className="flex-1 overflow-auto border-r">
      <Table>
        <TableHeader className="sticky top-0 bg-card z-10">
          <TableRow className="h-9">
            <TableHead>Event</TableHead>
            <TableHead>Phase</TableHead>
            <TableHead>Confirmed</TableHead>
            <TableHead>BBO</TableHead>
            <TableHead>Spread</TableHead>
            <TableHead>Depth@50</TableHead>
            <TableHead>Impact@1000</TableHead>
            <TableHead>Staleness</TableHead>
            <TableHead>Last Action</TableHead>
            <TableHead>PnL</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {/* Rows con h-9 */}
        </TableBody>
      </Table>
    </div>
    
    {/* Panel derecho (30%) */}
    <div className="w-[30%] overflow-auto p-3 space-y-3">
      <Card compact>
        <CardHeader className="p-3 pb-2">
          <CardTitle className="text-sm">Orderbook Health</CardTitle>
        </CardHeader>
        <CardContent className="p-3 pt-0 space-y-2">
          {/* Health metrics */}
        </CardContent>
      </Card>
      
      <Card compact>
        <CardHeader className="p-3 pb-2">
          <CardTitle className="text-sm">Precheck Failures</CardTitle>
        </CardHeader>
        <CardContent className="p-3 pt-0">
          {/* Breakdown */}
        </CardContent>
      </Card>
      
      <Card compact>
        <CardHeader className="p-3 pb-2">
          <CardTitle className="text-sm">Recent Orders</CardTitle>
        </CardHeader>
        <CardContent className="p-3 pt-0">
          {/* Orders list */}
        </CardContent>
      </Card>
    </div>
  </div>
</div>
```

#### 3.3 `/strategies/new` y `/strategies/[id]/edit` - Builder Compacto

**Estructura 3 Columnas**:
```tsx
<div className="flex gap-2 h-full">
  {/* Universe (izquierda) - 25% */}
  <div className="w-[25%] border-r p-3 space-y-2">
    <h3 className="text-sm font-semibold">Universe</h3>
    {/* Categories, Markets, Events, Deny, Auto-attach */}
  </div>
  
  {/* Knobs (centro) - 50% */}
  <div className="flex-1 p-3 space-y-2">
    <Accordion type="multiple" className="space-y-2">
      <AccordionItem value="orderbook" className="border rounded-lg">
        <AccordionTrigger className="px-3 py-2 text-sm">Orderbook Constraints</AccordionTrigger>
        <AccordionContent className="px-3 pb-3 space-y-2">
          <InlineForm label="Max Staleness (ms)" input={<Input type="number" defaultValue={2000} />} />
          {/* ... más knobs ... */}
        </AccordionContent>
      </AccordionItem>
      {/* ... más secciones ... */}
    </Accordion>
  </div>
  
  {/* Summary (derecha) - 25% */}
  <div className="w-[25%] border-l p-3 space-y-2">
    <h3 className="text-sm font-semibold">Summary</h3>
    {/* Validaciones y warnings */}
  </div>
</div>
```

---

### **FASE 4: Componentes Nuevos Compactos** (1-2 días)

#### 4.1 DenseTable Component

**Archivo**: `frontend/components/ui/dense-table.tsx` (nuevo)

```tsx
'use client';

import { useVirtualizer } from '@tanstack/react-virtual';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './table';

interface DenseTableProps<T> {
  data: T[];
  columns: Array<{
    key: keyof T;
    label: string;
    render?: (value: any, row: T) => React.ReactNode;
  }>;
  onRowHover?: (row: T) => void;
  rowHeight?: number;
}

export function DenseTable<T extends { id: string }>({
  data,
  columns,
  onRowHover,
  rowHeight = 36, // h-9
}: DenseTableProps<T>) {
  const parentRef = React.useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 10,
  });

  return (
    <div ref={parentRef} className="h-full overflow-auto">
      <Table>
        <TableHeader className="sticky top-0 bg-card z-10">
          <TableRow className="h-9">
            {columns.map(col => (
              <TableHead key={String(col.key)} className="px-3">
                {col.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {virtualizer.getVirtualItems().map(virtualRow => {
            const row = data[virtualRow.index];
            return (
              <TableRow
                key={row.id}
                className="h-9"
                onMouseEnter={() => onRowHover?.(row)}
              >
                {columns.map(col => (
                  <TableCell key={String(col.key)} className="px-3">
                    {col.render
                      ? col.render(row[col.key], row)
                      : String(row[col.key] ?? '')}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
```

#### 4.2 KPIBar Component

**Archivo**: `frontend/components/ui/kpi-bar.tsx` (nuevo)

```tsx
interface KPIProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
}

export function KPIBar({ kpis }: { kpis: KPIProps[] }) {
  return (
    <div className="flex items-center gap-4 px-3 py-2 border-b bg-card">
      {kpis.map((kpi, i) => (
        <div key={i} className="flex flex-col">
          <span className="text-[11px] text-muted-foreground">{kpi.label}</span>
          <span className="text-[13px] font-semibold">{kpi.value}</span>
        </div>
      ))}
    </div>
  );
}
```

#### 4.3 StatusPill Component

**Archivo**: `frontend/components/ui/status-pill.tsx` (nuevo)

```tsx
export function StatusPill({ status }: { status: 'active' | 'paused' | 'error' }) {
  const styles = {
    active: 'bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30',
    paused: 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/30',
    error: 'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30',
  };
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border ${styles[status]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${
        status === 'active' ? 'bg-green-500' :
        status === 'paused' ? 'bg-yellow-500' : 'bg-red-500'
      }`} />
      {status.toUpperCase()}
    </span>
  );
}
```

#### 4.4 MetricChip Component

**Archivo**: `frontend/components/ui/metric-chip.tsx` (nuevo)

```tsx
export function MetricChip({ 
  label, 
  value, 
  color = 'neutral' 
}: { 
  label: string; 
  value: string; 
  color?: 'green' | 'yellow' | 'red' | 'neutral';
}) {
  const colorStyles = {
    green: 'text-green-600 dark:text-green-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
    red: 'text-red-600 dark:text-red-400',
    neutral: 'text-foreground',
  };
  
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded border bg-card">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className={`text-[13px] font-medium ${colorStyles[color]}`}>{value}</span>
    </div>
  );
}
```

---

### **FASE 5: Eliminar "Colorines"** (0.5 día)

#### 5.1 Paleta Monocromática

**Archivo**: `frontend/app/globals.css`

**Cambios**:
- Eliminar colores vibrantes de charts
- Usar solo escala de grises + acentos sutiles
- Primary color: azul/gris neutro (no brillante)

```css
:root {
  /* Colores neutros, sin "colorines" */
  --primary: 217 20% 50%;        /* Gris azulado neutro */
  --primary-foreground: 0 0% 100%;
  
  /* Charts: escala de grises */
  --chart-1: 0 0% 40%;           /* Gris oscuro */
  --chart-2: 0 0% 50%;           /* Gris medio */
  --chart-3: 0 0% 60%;           /* Gris claro */
  --chart-4: 0 0% 70%;           /* Gris más claro */
  --chart-5: 0 0% 80%;           /* Gris muy claro */
  
  /* Status: sutiles */
  --success: 142 20% 40%;        /* Verde apagado */
  --warning: 45 20% 40%;         /* Amarillo apagado */
  --error: 0 20% 40%;            /* Rojo apagado */
}

.dark {
  /* Similar pero ajustado para dark */
}
```

#### 5.2 Revisar Componentes con Colores

**Archivos a revisar**:
- `frontend/components/Sidebar.tsx` - Eliminar `bg-green-500`, `bg-red-500`, etc.
- `frontend/components/markets/MarketCard.tsx` - Revisar colores
- Todos los componentes con `bg-*-500` hardcoded

**Reemplazar por**:
- `bg-success/20` en lugar de `bg-green-500/20`
- `text-success` en lugar de `text-green-600`
- Usar variables CSS siempre

---

## 📋 Checklist de Implementación

### FASE 1: Design Tokens (1 día)
- [ ] Ajustar tipografía a compacta (text-[13px] base)
- [ ] Ajustar spacing (px-3 py-2, gap-2)
- [ ] Añadir variantes compactas a Button (h-8, h-7)
- [ ] Ajustar Input a h-8
- [ ] Ajustar Table a h-9 rows, px-3 cells
- [ ] Ajustar Card a p-3, rounded-xl

### FASE 2: Layout (1 día)
- [ ] Compactar Layout principal (px-3 py-2)
- [ ] Compactar Sidebar (p-3, gap-2, text-[13px])
- [ ] Topbar compacto con search y acciones
- [ ] Keyboard shortcuts (/, flechas, Enter)

### FASE 3: Páginas (2-3 días)
- [ ] `/markets` - Tabla densa + panel lateral
- [ ] `/strategies/[id]/live` - Terminal split 70/30
- [ ] `/strategies/new|edit` - Builder 3 columnas
- [ ] `/strategies/[id]/simulate` - Modal compacto

### FASE 4: Componentes Nuevos (1-2 días)
- [ ] DenseTable con virtualización
- [ ] KPIBar
- [ ] StatusPill
- [ ] MetricChip
- [ ] InlineForm
- [ ] ConfirmModal

### FASE 5: Eliminar Colorines (0.5 día)
- [ ] Paleta monocromática
- [ ] Revisar y reemplazar colores hardcoded
- [ ] Charts en escala de grises

---

## 🎨 Principios de Diseño Final

1. **Alta densidad**: Más información, menos espacio
2. **Monocromático**: Sin colorines, solo grises + acentos sutiles
3. **Compacto**: text-[13px], h-8 inputs, h-9 table rows, px-3 py-2 spacing
4. **Keyboard-friendly**: / para search, flechas para navegar, Enter para aplicar
5. **Premium**: Skeleton loading, empty states útiles, micro-interacciones sutiles
6. **Trading terminal**: Tablas densas, métricas visibles, acciones primarias siempre accesibles

---

## 📝 Notas de Implementación

### Reutilización Máxima
- ✅ **NO reescribir** componentes existentes, solo ajustar
- ✅ **Reutilizar** hooks, utilidades, estructura
- ✅ **Mantener** shadcn/ui base, solo añadir variantes compactas
- ✅ **Preservar** funcionalidad existente

### Compatibilidad
- Mantener variantes existentes (`size="default"`) para compatibilidad
- Añadir nuevas variantes (`size="compact"`) para nuevo diseño
- Migración gradual página por página

### Testing
- Verificar que tablas con 1000+ rows no lag
- Verificar keyboard navigation
- Verificar responsive (mínimo 1280px)
- Verificar dark mode funciona correctamente

---

**Fin del Análisis**

