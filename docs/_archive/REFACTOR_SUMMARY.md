# Documentation Refactor Summary

**Date**: 2025-01-XX  
**Status**: IN PROGRESS

---

## Completed

### ✅ Folder Structure Created

- `docs/architecture/`
- `docs/strategies/` (with `examples/`)
- `docs/infrastructure/`
- `docs/risk/`
- `docs/backtesting/`
- `docs/operations/`
- `docs/compliance/`
- `docs/research/`
- `docs/adr/`
- `docs/onboarding/`
- `docs/exchange/`
- `docs/security/`
- `docs/_archive/`
- `docs/_triage/`

### ✅ Files Created

**New Consolidated Files:**
- `docs/strategies/README.md` - Strategy philosophy (merged STRATEGIES.md + strategies_theory.md)
- `docs/architecture/system-overview.md` - System overview (merged Executive_Summary + overall + algoritmo_backend)

**Missing Critical Docs (Skeletons):**
- `docs/operations/incident-response.md`
- `docs/operations/release-checklist.md`
- `docs/backtesting/framework.md`
- `docs/research/experiments.md`
- `docs/compliance/legal-notes.md`
- `docs/security/threat-model.md`
- `docs/security/secrets-handling.md`
- `docs/exchange/order-lifecycle.md`
- `docs/exchange/failure-modes.md`

**Moved:**
- `docs/EJEMPLO_ESTRATEGIA_COMPLETA.json` → `docs/strategies/examples/EJEMPLO_ESTRATEGIA_COMPLETA.json`

---

## In Progress

### ⏳ Files to Consolidate

**High Priority:**
- `docs/architecture/execution-engine.md` - Merge BACKEND_ARCHITECTURE_STRATEGIES + execution.md + signatures_trazability.md
- `docs/architecture/data-flow.md` - Merge scanner + event_mapping + checker + event_watch
- `docs/infrastructure/secrets.md` - Merge VARIABLES_ENTORNO + wallet_service
- `docs/infrastructure/monitoring.md` - Merge metrics_observabilitiy + LOGGING_CONFIG
- `docs/risk/controls.md` + `docs/risk/policy.md` - Split from risk_engine.md
- `docs/risk/kill-switch.md` - From runtime_supervisor.md
- `docs/backtesting/data-replay.md` - From historical_replay.md
- `docs/operations/runbook.md` - From livecontrol.md
- `docs/onboarding/quickstart.md` - Merge GUIA_INICIO + INSTALACION_DEPENDENCIAS

**Medium Priority:**
- `docs/exchange/polymarket-integration.md` - Merge POLYMARKET_CLIENT + WEBSOCKET + SCANNER_API
- `docs/architecture/quorum.md` - Merge QUORUM_* files
- `docs/architecture/config-driven.md` - Merge CONFIG_DRIVEN_* files
- `docs/research/roadmap.md` - Merge PLAN_* files

---

## Pending

### 📋 Files to Move/Archive

**To `docs/_archive/`:**
- Files from `docs/DONE/` that are historical
- Files from `docs/PENDING/` that are not merged

**To `docs/_triage/`:**
- Remaining `docs/PENDING/` files not merged

### 🗑️ Files to Delete

- `docs/DONE/ESTADO_ACTUAL_BACKEND.md`
- `docs/DONE/ESTADO_IMPLEMENTACION.md`
- `docs/DONE/RESUMEN_IMPLEMENTACION.md`
- `docs/DONE/PLAN_IMPLEMENTACION_STRATEGIES_V2_COMPLETADO.md`
- `docs/DONE/SERVIDORES_INICIADOS.md`
- `docs/DONE/ANALISIS_MIGRACION_STRATEGIES.md`
- `docs/DONE/strategy.md`
- `docs/PENDING/LIMPIEZA_DOCUMENTOS.md`
- `docs/PENDING/README.md`
- `docs/PENDING/RESUMEN_ESTADO_PENDIENTES.md`
- `frontend/FRONTEND_COMPLETE_REFACTOR.md`
- `frontend/FRONTEND_UX_FIXES_SUMMARY.md`
- `frontend/MIGRATION_SHADCN.md`
- `frontend/UX_PREMIUM_CHANGELOG.md`

### 📝 Files to Update

- `README.md` (root) - Add links to new structure
- `docs/README.md` - Create documentation index

---

## Notes

- All new files follow the required format (Purpose, Audience, Where this is used, Last updated)
- Open Questions sections added where details cannot be inferred
- History preserved by moving to `_archive/` instead of deleting (except explicitly listed deletions)

---

## Next Steps

1. Complete critical consolidations
2. Move/rename remaining files
3. Delete obsolete files
4. Update READMEs
5. Final review


