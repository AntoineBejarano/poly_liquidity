# Estado Phase 3 y qué falta para dejarlo perfecto

## ¿Hay fallos?

### Backend — **sin fallos**
- **Tests unitarios:** 840 passed (ejecutados con `pytest tests/unit -q`).
- **Tests de integración Phase 0, 1 y 2:** 22 passed (`test_phase0_directory_baseline`, `test_phase1_directory`, `test_phase2_universe`).
- No se modificó código backend en Phase 3; la suite pasa.

### Frontend — **sin fallos introducidos por Phase 3**
- **Build:** El fallo `EPERM: operation not permitted, rename ... server-reference-manifest.json` es de **permisos/entorno** (Windows, carpeta `.next` bloqueada o sandbox), no de código.
- **TypeScript:** El proyecto tiene **errores de TypeScript preexistentes** en otros archivos (`accessToken`, `CurrentUser`, `StrategyTemplate`, `lib/api.ts` headers, etc.). **Ninguno** de los archivos nuevos de Phase 3 aparece en la lista de errores:
  - `app/strategies/[id]/universe/page.tsx`
  - `components/strategy/universe/*`
  - `types/directory.ts`
- El único cambio en el Desk fue añadir el enlace "Configurar Universe" y el `import Link`; el error `StrategyTemplate` en `desk/page.tsx` ya existía (ese tipo no está exportado en `@/types/strategy`).

### Timeout de la suite completa
- Al ejecutar **toda** la suite (unit + integration), el timeout ocurre porque algunos tests de integración levantan la app completa, Redis, Scanner, etc., y pueden usar SQLite en memoria o tablas que no existen en ese contexto (`no such table: markets`). Eso es **configuración de entorno de tests**, no un fallo del código de Phase 3.

---

## Qué falta para que esté perfecto

### 1. **Phase 4 — Auto-attach seguro** (spec §3)
- Objetivo: que el control loop use Directory para auto-attach, con enabled global, deny_list, time_filter, límites (`max_events_per_strategy`, `max_auto_attaches_per_hour`) y dry-run.
- Todavía no implementado.

### 2. **Tests frontend para Universe (opcional)**
- Tests E2E o de integración que abran `/strategies/[id]/universe`, carguen filtros, simulen guardado y comprueben que no se llama a Gamma (ya cubierto en backend). Opcional para “perfecto” según la spec.

### 3. **Errores TypeScript/lint preexistentes del frontend**
- Para que el frontend compile y pase `tsc --noEmit` sin errores habría que corregir los fallos que ya existían (Stack Auth `CurrentUser`/`accessToken`, `StrategyTemplate`, `lib/api.ts`, tailwind, etc.). Son **ajenos a Phase 3** pero forman parte de “proyecto perfecto”.

### 4. **Entorno de tests backend**
- Para que la suite completa no haga timeout ni falle por DB:
  - Usar DB de test con migraciones aplicadas (o fixtures que creen tablas).
  - O marcar/skip tests que requieran tablas `markets`/events en entornos sin migraciones.

### 5. **Build frontend en CI/local**
- Si en tu máquina el build falla por EPERM, probar:
  - Cerrar dev server y otras instancias que usen `.next`.
  - Ejecutar build con permisos adecuados o fuera del sandbox.
  - En CI, usar un único job que construya sin conflictos de carpeta.

---

## Resumen ejecutivo

| Área              | ¿Fallos? | Notas                                              |
|-------------------|----------|----------------------------------------------------|
| Backend unit      | No       | 840 passed                                         |
| Backend integration (Phase 0–2) | No | 22 passed                                  |
| Phase 3 frontend  | No       | Código nuevo sin errores TS; build falla por EPERM |
| TS/lint resto frontend | Sí (preexistentes) | No introducidos por Phase 3           |
| Suite completa   | Timeout / DB | Entorno de tests (tablas, tiempo)              |

**Para dejarlo “perfecto”:**  
(1) Phase 4 (auto-attach), (2) opcionalmente tests frontend del Universe, (3) corregir TS/lint preexistentes del frontend, (4) ajustar entorno de tests para que la suite completa no haga timeout ni falle por tablas/DB.
