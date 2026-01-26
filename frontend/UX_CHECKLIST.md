UX Checklist - Prioridad para producto "premium"

1) Visión general
- Consistencia: definir escala de espaciado (8px), tipografías y jerarquía visual.
- Sistema de tokens: colores, radios, sombras, z-index, tamaños de texto.
- Densidad ajustable: compact/comfortable view para tablas y grids.

2) Componentes atómicos (UI kit)
- Botones: `primary`, `secondary`, `ghost`, `danger`.
- Inputs: text/number/select/checkbox/switch con `aria-*` y estados (error, help, success).
- Cards: `card` y `card-compact` con elevación/coherencia.
- Formularios: validación inline, mensajes amigables y accesibles.

3) Microinteracciones
- Transiciones suaves en hover/focus (duración 150-200ms, easing estándar).
- Feedback instantáneo para acciones críticas (toasts, banners no bloqueantes).
- Animaciones discretas en carga y cambios de estado.

4) Data & Charts
- Mostrar contexto: time range selector, aggregation (1m/5m/1h/1d).
- Charts significativos: P&L timeseries, latencia por etapa, éxito/rechazo por volumen.
- Resumen numérico encima de cada gráfico (trend, delta, %).
- Lazy-load y limitación de puntos para performance.

5) Accesibilidad
- Roles y `aria-*` en controles interactivos.
- Keyboard-first: tabbable controls, visible focus outline.
- Contraste mínimo WCAG AA; probar en black mode.

6) Error handling & states
- Skeletons y placeholders en lugar de huecos visuales.
- Toaster para errores; modales sólo para confirmaciones importantes.
- Límites en la visualización de JSON/objetos grandes.

7) Polished visuals
- Tipografía variable o Inter variable; kerning y optical sizing.
- Elevaciones sutiles y bordes redondeados consistentes.
- Iconografía coherente (lucide) y tamaños alineados.

8) QA & Delivery
- Storybook + visual regression (Chromatic/Playwright snapshots).
- Lighthouse CI en pipeline con thresholds (performance, accessibility).
- E2E (Playwright) para flujos críticos: login, crear estrategia, ejecución simulada.

Notas rápidas de prioridad:
- Inmediato: toasts en lugar de alert, limitar JSON, ARIA en formularios, ThemeToggle.
- Medio plazo: UI kit completo, Storybook, charts con sampling y resumen numérico.
- Largo plazo: observabilidad de UX (RUM), tests visuales y A/B para microinteractions.
