# Listo para testear — Discovery / Universe / Strategy Builder

## ¿Está todo listo?

Sí. Backend (Phase 0–4), frontend (Phase 3) y alineación están listos para pruebas end-to-end.

---

## Base de datos (DB)

**No hay que tocar nada** en la DB para estas fases.

- **Phase 0–4** usan estructuras ya existentes:
  - `strategies.universe_config` (JSONB) — ya existía; solo se añaden/usan más claves en el JSON (time_filter, events, max_events_per_strategy, etc.).
  - Directory usa: `markets`, `events`, `tags`, `market_tag`, `market_enabled_states` (todo ya existente).
- No se crearon **nuevas tablas ni columnas**; no hace falta **nueva migración de Alembic**.
- Si tu entorno ya tiene aplicadas las migraciones (incl. `add_universe_config_to_strategies`), no hay pasos extra.

---

## Frontend ↔ Backend (alineación y conexión)

- **Rutas que usa el frontend:**
  - `GET /directory/meta` — freshness
  - `GET /directory/categories` — listado categorías
  - `GET /directory/tags?limit=200` — listado tags
  - `GET /directory/events?…` — eventos con filtros (category, tag_id, state, next_days)
  - `GET /api/strategies/{id}` — nombre estrategia
  - `GET /api/strategies/{id}/universe` — universo actual (incl. Phase 4 si existen)
  - `PUT /api/strategies/{id}/universe` — guardar universo
- **Alineación:**
  - Al **guardar** desde la página Universe, se hace **merge** con el universo actual: solo se envían los cambios de filtros (categorías, tags, time_filter) y se **preservan** auto_attach, deny_list, markets, events y campos Phase 4 (max_events_per_strategy, max_auto_attaches_per_hour, auto_attach_dry_run).
  - Tipos en `frontend/types/directory.ts` incluyen Phase 4; el resumen en la UI muestra límites y dry-run cuando vienen del backend.

---

## Cómo testear (resumen)

1. **Backend** levantado (p. ej. `uvicorn` / `run_server.py`) y **DB** con migraciones aplicadas.
2. **Frontend** levantado (p. ej. `npm run dev`).
3. **Desk** → elegir una estrategia → enlace **«Configurar Universe»** → va a `/strategies/{id}/universe`.
4. En **Universe**: filtrar por categoría/tag/tiempo, ver lista de eventos (Directory), revisar resumen y **Guardar**. Comprobar que al recargar se mantienen los valores guardados y que no se pierden auto_attach ni límites Phase 4 si ya estaban configurados (p. ej. por API).
5. **Auto-attach (Phase 4)**: configurar universo con `auto_attach: true` (por API o en el futuro desde la UI) y, si aplica, límites y dry-run; comprobar en logs del control loop que se usan Directory, límites y dry-run según lo configurado.

---

## Limitaciones actuales (opcionales para más adelante)

- La página Universe **no** tiene aún controles para editar **auto_attach**, **deny_list** ni los **límites Phase 4**; esos valores se pueden setear por API y se **conservan** al guardar solo filtros desde la UI.
- Tests E2E del frontend (Universe) no están en el repo; los tests de integración del backend (Phase 0–4) sí están y pasan.

Con esto, **sí está todo listo para testear** (backend, front, DB y alineación), sin tocar la DB.
