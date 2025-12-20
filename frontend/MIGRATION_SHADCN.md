Plan de migración a `shadcn` components

Objetivo: usar el set de componentes `shadcn/ui` (o su equivalente) para mantener consistencia, accesibilidad y theming centralizado.

Pasos propuestos (incrementales):

1) Preparación
- Añadir `shadcn/ui` y dependencias recomendadas (si aplica a la stack). Revisar licencias.
- Configurar tokens únicos y mapear variables actuales (`--primary`, `--card`, etc.).

2) Components core (fase 1)
- Migrar `Button`, `Input`, `Card` a implementaciones basadas en `shadcn` primitives.
- Mantener API local (props `variant`, `compact`) para reemplazos transparentes.
- Crear wrapper `components/ui/*` que exponga la API antigua.

3) Documentación y Storybook
- Añadir Storybook mínimo y documentar cada componente con estados (hover, focus, disabled, error).
- Incluir visual regression snapshots.

4) Migración por capas (fase 2)
- Refactorizar componentes de mayor impacto (header, forms, tables, timeline) en orden de prioridad.
- Para cada refactor: actualizar tests unitarios/E2E y PRs pequeños.

5) Theming
- Validar `next-themes` y aplicar clases `light`/`dark`/`black` a raíz.
- Asegurar que `shadcn` tokens respeten variables definidas en `app/globals.css`.

6) QA
- Ejecutar Lighthouse y pruebas de accesibilidad (axe).
- Realizar pruebas visuales contra staging.

7) Rollout
- Lanzamiento gradual con feature flags para secciones críticas de trading.
- Monitorizar errores y métricas UX (RUM).

Estimación de tiempo:
- Core UI kit + Storybook: 1-2 días.
- Migración de 5-7 componentes críticos: 2-3 días.
- QA y rollout: 1-2 días.

Riesgos y mitigaciones:
- Breaking changes en estilos: utilizar wrapper components y un tema de compatibilidad.
- Dependencias: fijar versiones y ejecutar pruebas de integración en CI.

Notas finales:
- Puedo automatizar la generación de wrappers y crear PRs por grupo de componentes si quieres que lo haga.
