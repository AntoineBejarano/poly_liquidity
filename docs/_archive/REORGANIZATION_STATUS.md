# Estado de Reorganización de Documentación

**Fecha**: 2025-01-XX  
**Estado**: ✅ Estructura Completada - Limpieza Pendiente

---

## ✅ Completado

### Estructura de Carpetas
- ✅ `docs/architecture/` - Arquitectura del sistema
- ✅ `docs/strategies/` - Estrategias de trading
- ✅ `docs/infrastructure/` - Infraestructura y configuración
- ✅ `docs/risk/` - Gestión de riesgo
- ✅ `docs/backtesting/` - Backtesting y replay
- ✅ `docs/operations/` - Operaciones y runbooks
- ✅ `docs/compliance/` - Compliance y legal
- ✅ `docs/research/` - Investigación y roadmap
- ✅ `docs/onboarding/` - Guías de inicio
- ✅ `docs/exchange/` - Integración con exchange
- ✅ `docs/security/` - Seguridad
- ✅ `docs/adr/` - Architecture Decision Records
- ✅ `docs/_archive/` - Archivos históricos
- ✅ `docs/_triage/` - Archivos pendientes de revisión

### Archivos Consolidados

**Architecture:**
- ✅ `architecture/system-overview.md` - Visión general del sistema
- ✅ `architecture/data-flow.md` - Flujo de datos (Scanner → Execution)
- ✅ `architecture/execution-engine.md` - Execution Engine y firmas
- ✅ `architecture/quorum.md` - Sistema de quorum
- ✅ `architecture/config-driven.md` - Arquitectura config-driven

**Infrastructure:**
- ✅ `infrastructure/secrets.md` - Gestión de secretos y variables
- ✅ `infrastructure/monitoring.md` - Métricas y observabilidad

**Risk:**
- ✅ `risk/controls.md` - Controles de riesgo y exposición
- ✅ `risk/policy.md` - Políticas de riesgo
- ✅ `risk/kill-switch.md` - Circuit breakers y fail-safes

**Operations:**
- ✅ `operations/runbook.md` - Runbook operativo
- ✅ `operations/incident-response.md` - Respuesta a incidentes
- ✅ `operations/release-checklist.md` - Checklist de release
- ✅ `operations/troubleshooting.md` - Troubleshooting

**Backtesting:**
- ✅ `backtesting/framework.md` - Framework de backtesting
- ✅ `backtesting/data-replay.md` - Historical Replay

**Onboarding:**
- ✅ `onboarding/quickstart.md` - Guía rápida de inicio

**Exchange:**
- ✅ `exchange/polymarket-integration.md` - Integración Polymarket
- ✅ `exchange/order-lifecycle.md` - Ciclo de vida de órdenes
- ✅ `exchange/failure-modes.md` - Manejo de fallos

**Strategies:**
- ✅ `strategies/README.md` - Filosofía y tipos de estrategias
- ✅ `strategies/examples/` - Ejemplos de estrategias

**Research:**
- ✅ `research/experiments.md` - Guías de experimentos
- ✅ `research/roadmap.md` - Roadmap y planes futuros

**Compliance:**
- ✅ `compliance/legal-notes.md` - Notas legales

**Security:**
- ✅ `security/threat-model.md` - Modelo de amenazas
- ✅ `security/secrets-handling.md` - Manejo de secretos

**ADR:**
- ✅ `adr/decisions.md` - Decisiones de arquitectura

**Índice:**
- ✅ `docs/README.md` - Índice completo de documentación

---

## ⏳ Pendiente de Limpieza

### Archivos en `DONE/` (Ya Consolidados)

Estos archivos ya fueron consolidados en los nuevos archivos. Deben moverse a `_archive/`:

- `algoritmo_backend.md` → Consolidado en `architecture/system-overview.md`
- `checker_system.md` → Consolidado en `architecture/data-flow.md`
- `event_mapping_layer.md` → Consolidado en `architecture/data-flow.md`
- `event_watch_engine.md` → Consolidado en `architecture/data-flow.md`
- `execution.md` → Consolidado en `architecture/execution-engine.md`
- `historical_replay.md` → Consolidado en `backtesting/data-replay.md`
- `livecontrol.md` → Consolidado en `operations/runbook.md`
- `metrics_observabilitiy.md` → Consolidado en `infrastructure/monitoring.md`
- `POLYMARKET_CLIENT_INTEGRATION.md` → Consolidado en `exchange/polymarket-integration.md`
- `POLYMARKET_WEBSOCKET_INTEGRATION.md` → Consolidado en `exchange/polymarket-integration.md`
- `risk_engine.md` → Consolidado en `risk/controls.md` y `risk/policy.md`
- `runtime_supervisor.md` → Consolidado en `risk/kill-switch.md` y `infrastructure/monitoring.md`
- `scanner.md` → Consolidado en `architecture/data-flow.md`
- `signatures_trazability.md` → Consolidado en `architecture/execution-engine.md`
- `wallet_service.md` → Consolidado en `infrastructure/secrets.md`

**Archivos específicos que pueden mantenerse o archivarse:**
- `SCANNER_API_ANALYSIS.md` → Consolidado en `architecture/data-flow.md`
- `QUORUM_DINAMICO_IMPLEMENTADO.md` → Consolidado en `architecture/quorum.md`
- `FRONTEND_CONFIG_DECISION_TRACES.md` → Evaluar si mover a `_triage/` o eliminar
- `tech_view.md` → Muy largo, evaluar si dividir o archivar

### Archivos en `GENERAL_EXPLANATIONS/` (Ya Consolidados)

- `Executive_Summary.md` → Consolidado en `architecture/system-overview.md`
- `GUIA_INICIO.md` → Consolidado en `onboarding/quickstart.md`
- `overall.md` → Consolidado en `architecture/system-overview.md`
- `strategies_theory.md` → Consolidado en `strategies/README.md`
- `VALIDACION_REGLAS_TRADING.md` → Consolidado en `risk/policy.md`

### Archivos en `PENDING/` (Evaluar)

**Para consolidar:**
- `PARAMETROS_PROTEGIDOS.md` → Consolidar en `risk/policy.md`
- `DECISION_TRACE_GUIDELINES.md` → Consolidar en `operations/troubleshooting.md`
- `GUIA_PLANTILLAS_ESTRATEGIAS.md` → Mover a `strategies/` o consolidar

**Para archivar en `_triage/`:**
- `CONFIG_DRIVEN_ARCHITECTURE.md` → Ya consolidado en `architecture/config-driven.md`
- `CONFIG_DRIVEN_SUMMARY.md` → Ya consolidado
- `QUORUM_DINAMICO_REQUISITOS.md` → Ya consolidado en `architecture/quorum.md`
- `QUORUM_SEMANTICA_CORREGIDA.md` → Ya consolidado
- `QUORUM_VIOLACIONES.md` → Ya consolidado

**Para mover a `research/roadmap.md`:**
- `PLAN_IMPLEMENTACION_INDICADORES_AVANZADOS.md`
- `PLAN_IMPLEMENTACION_SERIES_MARKETS.md`
- `PLAN_MEJORA_LATENCY_Y_UX.md`
- `SERIES_MARKETS.md`
- `PLAN_CARGA_SEPARADA_COMPONENTES.md`

**Para eliminar (meta-documentación):**
- `LIMPIEZA_DOCUMENTOS.md`
- `README.md`
- `RESUMEN_ESTADO_PENDIENTES.md`

**Para evaluar:**
- `ARQUITECTURA_UX_PLATAFORMA_TRADING.md` → Mover a `_triage/` o eliminar
- `FRONTEND_API_ENDPOINTS.md` → Mover a `_triage/` o eliminar
- `template_estrategy_live_control.html` → Mover a `_triage/` o eliminar

### Archivos en Raíz de `docs/` (Mover)

- `STRATEGIES.md` → Ya consolidado en `strategies/README.md` (eliminar)
- `BACKEND_ARCHITECTURE_STRATEGIES.md` → Ya consolidado en `architecture/execution-engine.md` (eliminar)
- `VARIABLES_ENTORNO.md` → Ya consolidado en `infrastructure/secrets.md` (eliminar)
- `EJEMPLO_ESTRATEGIA_COMPLETA.json` → Ya movido a `strategies/examples/` (eliminar duplicado si existe)

### Archivos Históricos (Eliminar)

Estos archivos ya no son relevantes y deben eliminarse:

- `docs/DONE/ESTADO_ACTUAL_BACKEND.md` (si existe)
- `docs/DONE/ESTADO_IMPLEMENTACION.md` (si existe)
- `docs/DONE/RESUMEN_IMPLEMENTACION.md` (si existe)
- `docs/DONE/PLAN_IMPLEMENTACION_STRATEGIES_V2_COMPLETADO.md` (si existe)
- `docs/DONE/SERVIDORES_INICIADOS.md` (si existe)
- `docs/DONE/ANALISIS_MIGRACION_STRATEGIES.md` (si existe)
- `docs/DONE/strategy.md` (si existe)

---

## 📋 Próximos Pasos

1. ⏳ Mover archivos consolidados de `DONE/` a `_archive/`
2. ⏳ Mover archivos consolidados de `GENERAL_EXPLANATIONS/` a `_archive/`
3. ⏳ Procesar archivos de `PENDING/` (consolidar, archivar o eliminar)
4. ⏳ Eliminar archivos obsoletos e históricos
5. ⏳ Actualizar referencias en `README.md` principal si es necesario
6. ⏳ Verificar que no haya enlaces rotos

---

## ✅ Resumen

**Estado General**: La reorganización está **completada en su mayor parte**. La estructura está creada, los archivos críticos están consolidados, y el índice está actualizado. Solo falta la limpieza final de archivos antiguos.

**Documentación Crítica**: ✅ Todas las secciones críticas para producción están documentadas y organizadas.

**Accesibilidad**: ✅ La documentación está organizada de forma lógica y fácil de navegar.

