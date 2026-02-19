# Premium Fintech Design System

Paleta y tokens para consistencia entre dark y light mode.

## Palette (HEX referencia)

**Light mode:** Emerald primary, blue secondary.  
**Dark mode (institutional terminal):** Low-saturation green, steel blue. No neon, no violet.

| Token | Light | Dark | Uso |
|-------|-------|------|-----|
| Primary | `#10B981` | `#4A6B5A` (institutional green) | CTA, nav activo |
| Secondary accent | `#3B82F6` | `#6B8BA8` (steel blue) | Info, links |
| Background | `#FAFAFA` | `#0F1114` | Fondo principal (charcoal) |
| Card | `#FFFFFF` | `#16181D` | Superficie de panel |
| Elevated | `#FFFFFF` | `#1A1D23` | Modales, dropdowns |
| Foreground | — | `#E8EAED` | Texto principal |
| Muted foreground | `#6B7280` | `#9AA0AB` | Labels, captions |
| Border | `#E5E7EB` | `#262A32` | Bordes suaves (hairline) |

## CSS Variables (HSL)

```css
:root {
  --background: 0 0% 98%;
  --foreground: 220 13% 10%;
  --card: 0 0% 100%;
  --elevated: 0 0% 100%;
  --primary: 160 84% 39%;           /* emerald */
  --accent-secondary: 217 91% 60%;  /* blue */
  --muted-foreground: 220 9% 46%;
  --border: 220 13% 88%;
  --border-subtle: 220 13% 92%;
  --input: 220 13% 92%;
  --ring: 160 84% 39%;
  --radius: 0.375rem;
  --radius-lg: 0.5rem;
}
```

## Clases de superficie

- `surface-page` — Fondo profundo
- `surface-panel` — Panel con sombra sutil
- `surface-elevated` — Superficie elevada (modales)

## Sidebar (default / hover / active)

```tsx
// Default
"text-muted-foreground"

// Hover
"hover:bg-accent/60 hover:text-foreground"

// Active
"bg-primary/10 text-primary font-medium"
+ barra izquierda: "w-0.5 h-4 rounded-full bg-primary"
```

## Inputs

- Default: `border-input`, `bg-background`
- Hover: `border-[hsl(var(--border))]`
- Focus: `ring-[1px]` + `shadow-[0_0_0_3px_hsl(var(--ring)/0.12)]`
- Error: `aria-[invalid=true]` → `border-[hsl(var(--error))]`
- Disabled: `opacity-50`

## Botones

- **Primary**: `bg-primary text-primary-foreground`
- **Secondary**: `bg-secondary text-secondary-foreground`
- **Ghost**: `hover:bg-accent hover:text-accent-foreground`
- **Outline**: `border border-input` + hover sutil

## Tipografía

- `text-h1` — 1.125rem, peso 600
- `text-h2` — 0.9375rem
- `text-h3` — 0.8125rem
- `text-body` — 0.8125rem, line-height 1.5rem
- `text-label` — 0.75rem, `text-muted-foreground`
- `text-caption` — 0.6875rem, max-width 42ch
- `tabular-nums` — Números alineados
