# Auditoría y Reorganización de Documentación

**Fecha**: 2025-01-XX  
**Objetivo**: Reorganizar documentación para producción, eliminar redundancias, consolidar estrategias, y crear estructura clara para ingenieros e investigadores.

---

## 📋 Inventario de Documentación Existente

### Raíz del Proyecto

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `README.md` | Documentación principal del proyecto | ✅ Actualizado | Mantener, actualizar con nueva estructura |
| `VALIDACION_REGLAS_TRADING.md` | Validación de reglas de trading | ⚠️ Duplicado | Mover a `docs/risk/` y eliminar duplicado |

### docs/ (Raíz)

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `README.md` | Índice de documentación | ⚠️ Desactualizado | Reemplazar con nuevo índice |
| `STRATEGIES.md` | Diseño y filosofía de estrategias | ✅ Relevante | Consolidar en `docs/strategies/README.md` |
| `BACKEND_ARCHITECTURE_STRATEGIES.md` | Arquitectura basada en grafos | ✅ Crítico | Mover a `docs/architecture/execution-engine.md` |
| `VARIABLES_ENTORNO.md` | Variables de entorno | ✅ Relevante | Mover a `docs/infrastructure/secrets.md` |
| `EJEMPLO_ESTRATEGIA_COMPLETA.json` | Ejemplo de estrategia | ✅ Útil | Mover a `docs/strategies/examples/` |

### docs/DONE/ (Implementaciones Completadas)

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `algoritmo_backend.md` | Algoritmo del backend | ⚠️ Redundante | Consolidar en `docs/architecture/system-overview.md` |
| `ANALISIS_MIGRACION_STRATEGIES.md` | Análisis de migración | ⚠️ Histórico | Archivar o eliminar |
| `checker_system.md` | Sistema de checkers | ✅ Relevante | Mover a `docs/architecture/data-flow.md` |
| `ESTADO_ACTUAL_BACKEND.md` | Estado actual | ⚠️ Desactualizado | Eliminar |
| `ESTADO_IMPLEMENTACION.md` | Estado implementación | ⚠️ Histórico | Eliminar |
| `event_mapping_layer.md` | Event Mapping Layer | ✅ Relevante | Mover a `docs/architecture/data-flow.md` |
| `event_watch_engine.md` | Event Watch Engine | ✅ Relevante | Mover a `docs/architecture/data-flow.md` |
| `execution.md` | Execution Engine | ✅ Crítico | Mover a `docs/architecture/execution-engine.md` |
| `FRONTEND_CONFIG_DECISION_TRACES.md` | Frontend config | ⚠️ Específico | Mover a `docs/frontend/` o eliminar |
| `historical_replay.md` | Historical Replay | ✅ Relevante | Mover a `docs/backtesting/data-replay.md` |
| `INSTALACION_DEPENDENCIAS.md` | Instalación | ⚠️ Redundante | Consolidar en `docs/onboarding/quickstart.md` |
| `livecontrol.md` | Live Control | ✅ Relevante | Mover a `docs/operations/runbook.md` |
| `metrics_observabilitiy.md` | Métricas y observabilidad | ✅ Relevante | Mover a `docs/infrastructure/monitoring.md` |
| `PLAN_IMPLEMENTACION_STRATEGIES_V2_COMPLETADO.md` | Plan completado | ⚠️ Histórico | Eliminar |
| `POLYMARKET_CLIENT_INTEGRATION.md` | Integración Polymarket | ✅ Relevante | Mover a `docs/architecture/data-flow.md` |
| `POLYMARKET_WEBSOCKET_INTEGRATION.md` | WebSocket integration | ✅ Relevante | Mover a `docs/architecture/data-flow.md` |
| `QUORUM_DINAMICO_IMPLEMENTADO.md` | Quorum dinámico | ⚠️ Específico | Consolidar en `docs/architecture/data-flow.md` |
| `RESUMEN_IMPLEMENTACION.md` | Resumen implementación | ⚠️ Histórico | Eliminar |
| `risk_engine.md` | Risk Engine | ✅ Crítico | Mover a `docs/risk/position-sizing.md` y `docs/risk/limits.md` |
| `runtime_supervisor.md` | Runtime Supervisor | ✅ Crítico | Mover a `docs/risk/kill-switch.md` y `docs/infrastructure/monitoring.md` |
| `SCANNER_API_ANALYSIS.md` | Análisis Scanner API | ⚠️ Específico | Consolidar en `docs/architecture/data-flow.md` |
| `scanner.md` | Scanner Engine | ✅ Relevante | Mover a `docs/architecture/data-flow.md` |
| `SERVIDORES_INICIADOS.md` | Servidores iniciados | ⚠️ Histórico | Eliminar |
| `signatures_trazability.md` | Firmas y trazabilidad | ✅ Relevante | Mover a `docs/architecture/execution-engine.md` |
| `strategy.md` | Strategy Engine (antiguo) | ⚠️ Desactualizado | Reemplazar con `docs/strategies/` |
| `tech_view.md` | Vista técnica detallada | ⚠️ Muy largo | Dividir en múltiples archivos |
| `wallet_service.md` | Wallet Service | ✅ Relevante | Mover a `docs/infrastructure/secrets.md` |

### docs/GENERAL_EXPLANATIONS/

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `Executive_Summary.md` | Resumen ejecutivo | ✅ Relevante | Consolidar en `docs/architecture/system-overview.md` |
| `GUIA_INICIO.md` | Guía de inicio | ⚠️ Redundante | Consolidar en `docs/onboarding/quickstart.md` |
| `overall.md` | Visión general | ⚠️ Redundante | Consolidar en `docs/architecture/system-overview.md` |
| `strategies_theory.md` | Teoría de estrategias | ✅ Relevante | Mover a `docs/strategies/README.md` |
| `VALIDACION_REGLAS_TRADING.md` | Validación reglas | ⚠️ Duplicado | Mover a `docs/risk/limits.md` |

### docs/PENDING/ (Pendientes)

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `ARQUITECTURA_UX_PLATAFORMA_TRADING.md` | Arquitectura UX | ⚠️ Pendiente | Mover a `docs/frontend/` o eliminar si no relevante |
| `CONFIG_DRIVEN_ARCHITECTURE.md` | Arquitectura config-driven | ⚠️ Pendiente | Consolidar en `docs/architecture/` |
| `CONFIG_DRIVEN_SUMMARY.md` | Resumen config-driven | ⚠️ Pendiente | Consolidar en `docs/architecture/` |
| `DECISION_TRACE_GUIDELINES.md` | Guías de decision trace | ⚠️ Pendiente | Mover a `docs/operations/troubleshooting.md` |
| `FRONTEND_API_ENDPOINTS.md` | Endpoints frontend | ⚠️ Pendiente | Mover a `docs/frontend/` o eliminar |
| `GUIA_PLANTILLAS_ESTRATEGIAS.md` | Guía plantillas | ⚠️ Pendiente | Mover a `docs/strategies/` |
| `LIMPIEZA_DOCUMENTOS.md` | Limpieza docs | ⚠️ Meta | Eliminar después de reorganización |
| `PARAMETROS_PROTEGIDOS.md` | Parámetros protegidos | ✅ Relevante | Mover a `docs/risk/limits.md` |
| `PLAN_CARGA_SEPARADA_COMPONENTES.md` | Plan carga separada | ⚠️ Pendiente | Evaluar relevancia |
| `PLAN_IMPLEMENTACION_INDICADORES_AVANZADOS.md` | Plan indicadores | ⚠️ Pendiente | Mover a `docs/research/roadmap.md` |
| `PLAN_IMPLEMENTACION_SERIES_MARKETS.md` | Plan series markets | ⚠️ Pendiente | Mover a `docs/research/roadmap.md` |
| `PLAN_MEJORA_LATENCY_Y_UX.md` | Plan mejora latencia | ⚠️ Pendiente | Mover a `docs/research/roadmap.md` |
| `QUORUM_DINAMICO_REQUISITOS.md` | Requisitos quorum | ⚠️ Pendiente | Consolidar en `docs/architecture/data-flow.md` |
| `QUORUM_SEMANTICA_CORREGIDA.md` | Semántica quorum | ⚠️ Pendiente | Consolidar en `docs/architecture/data-flow.md` |
| `QUORUM_VIOLACIONES.md` | Violaciones quorum | ⚠️ Pendiente | Consolidar en `docs/architecture/data-flow.md` |
| `README.md` | README pendientes | ⚠️ Meta | Eliminar después de reorganización |
| `RESUMEN_ESTADO_PENDIENTES.md` | Resumen pendientes | ⚠️ Meta | Eliminar después de reorganización |
| `SERIES_MARKETS.md` | Series markets | ⚠️ Pendiente | Mover a `docs/research/roadmap.md` |
| `template_estrategy_live_control.html` | Template HTML | ⚠️ Específico | Mover a `docs/frontend/` o eliminar |

### backend/docs/

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `LOGGING_CONFIG.md` | Configuración de logging | ✅ Relevante | Mover a `docs/infrastructure/monitoring.md` |

### backend/tests/integration/

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `README.md` | Tests de integración | ✅ Relevante | Mantener en lugar |
| `INSTRUCCIONES.md` | Instrucciones tests | ✅ Relevante | Mantener en lugar |

### frontend/

| Archivo | Propósito | Estado | Acción Propuesta |
|---------|-----------|--------|------------------|
| `FRONTEND_COMPLETE_REFACTOR.md` | Refactor frontend | ⚠️ Histórico | Eliminar |
| `FRONTEND_UX_FIXES_SUMMARY.md` | Fixes UX | ⚠️ Histórico | Eliminar |
| `MIGRATION_SHADCN.md` | Migración ShadCN | ⚠️ Histórico | Eliminar |
| `PLAN_UX_PREMIUM.md` | Plan UX premium | ⚠️ Pendiente | Mover a `docs/research/roadmap.md` |
| `UX_CHECKLIST.md` | Checklist UX | ⚠️ Pendiente | Mover a `docs/frontend/` o eliminar |
| `UX_PREMIUM_CHANGELOG.md` | Changelog UX | ⚠️ Histórico | Eliminar |

---

## 🎯 Propuesta de Nueva Estructura

### Estructura Objetivo

```
docs/
├── architecture/
│   ├── system-overview.md          # Visión general consolidada
│   ├── data-flow.md                # Flujo de datos (Scanner → Execution)
│   └── execution-engine.md          # Execution Engine y firmas
├── strategies/
│   ├── README.md                   # Filosofía y tipos de estrategias
│   ├── market-making.md            # Estrategia de market making
│   ├── arbitrage.md                # Estrategias de arbitraje
│   └── signal-based.md            # Estrategias basadas en señales
├── infrastructure/
│   ├── cloud-setup.md              # Setup en cloud (Docker, etc.)
│   ├── containers.md               # Docker y contenedores
│   ├── ci-cd.md                    # CI/CD (si aplica)
│   ├── secrets.md                  # Gestión de secretos y variables
│   └── monitoring.md               # Métricas, logging, observabilidad
├── risk/
│   ├── position-sizing.md          # Cálculo de tamaños de posición
│   ├── limits.md                   # Límites y reglas de riesgo
│   └── kill-switch.md              # Circuit breakers y fail-safes
├── backtesting/
│   ├── framework.md                # Framework de backtesting
│   └── data-replay.md              # Historical Replay
├── operations/
│   ├── runbook.md                  # Runbook operativo
│   ├── incident-response.md        # Respuesta a incidentes
│   └── troubleshooting.md          # Troubleshooting común
├── compliance/
│   └── legal-notes.md              # Notas legales y compliance
├── research/
│   ├── experiments.md              # Cómo ejecutar experimentos
│   └── roadmap.md                  # Roadmap y planes futuros
├── adr/
│   └── decisions.md                # Architecture Decision Records
└── onboarding/
    └── quickstart.md                # Guía rápida de inicio
```

---

## 📊 Mapeo de Archivos Existentes → Nueva Estructura

### architecture/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `system-overview.md` | `GENERAL_EXPLANATIONS/Executive_Summary.md`<br>`GENERAL_EXPLANATIONS/overall.md`<br>`DONE/algoritmo_backend.md` (consolidado) |
| `data-flow.md` | `DONE/scanner.md`<br>`DONE/event_mapping_layer.md`<br>`DONE/checker_system.md`<br>`DONE/event_watch_engine.md`<br>`DONE/POLYMARKET_CLIENT_INTEGRATION.md`<br>`DONE/POLYMARKET_WEBSOCKET_INTEGRATION.md`<br>`DONE/SCANNER_API_ANALYSIS.md` |
| `execution-engine.md` | `BACKEND_ARCHITECTURE_STRATEGIES.md`<br>`DONE/execution.md`<br>`DONE/signatures_trazability.md` |

### strategies/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `README.md` | `STRATEGIES.md`<br>`GENERAL_EXPLANATIONS/strategies_theory.md` |
| `market-making.md` | (Nuevo - extraer de ejemplos) |
| `arbitrage.md` | (Nuevo - extraer de ejemplos) |
| `signal-based.md` | (Nuevo - extraer de ejemplos) |

### infrastructure/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `cloud-setup.md` | `DONE/tech_view.md` (sección despliegue)<br>`docker-compose.yml` (referencia) |
| `containers.md` | `backend/Dockerfile` (referencia) |
| `secrets.md` | `VARIABLES_ENTORNO.md`<br>`DONE/wallet_service.md` |
| `monitoring.md` | `DONE/metrics_observabilitiy.md`<br>`backend/docs/LOGGING_CONFIG.md`<br>`DONE/runtime_supervisor.md` (sección monitoreo) |

### risk/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `position-sizing.md` | `DONE/risk_engine.md` (sección sizing) |
| `limits.md` | `DONE/risk_engine.md` (sección límites)<br>`PENDING/PARAMETROS_PROTEGIDOS.md`<br>`VALIDACION_REGLAS_TRADING.md` |
| `kill-switch.md` | `DONE/runtime_supervisor.md` (sección circuit breakers) |

### backtesting/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `framework.md` | (Nuevo - documentar framework) |
| `data-replay.md` | `DONE/historical_replay.md` |

### operations/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `runbook.md` | `DONE/livecontrol.md` |
| `incident-response.md` | (Nuevo - crear) |
| `troubleshooting.md` | `PENDING/DECISION_TRACE_GUIDELINES.md` |

### research/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `experiments.md` | (Nuevo - crear) |
| `roadmap.md` | `PENDING/PLAN_IMPLEMENTACION_INDICADORES_AVANZADOS.md`<br>`PENDING/PLAN_IMPLEMENTACION_SERIES_MARKETS.md`<br>`PENDING/PLAN_MEJORA_LATENCY_Y_UX.md`<br>`PENDING/SERIES_MARKETS.md`<br>`frontend/PLAN_UX_PREMIUM.md` |

### onboarding/

| Nuevo Archivo | Contenido de Archivos Existentes |
|---------------|----------------------------------|
| `quickstart.md` | `GENERAL_EXPLANATIONS/GUIA_INICIO.md`<br>`DONE/INSTALACION_DEPENDENCIAS.md`<br>`README.md` (sección setup) |

---

## 🗑️ Archivos a Eliminar

### Históricos / Desactualizados
- `docs/DONE/ESTADO_ACTUAL_BACKEND.md`
- `docs/DONE/ESTADO_IMPLEMENTACION.md`
- `docs/DONE/RESUMEN_IMPLEMENTACION.md`
- `docs/DONE/PLAN_IMPLEMENTACION_STRATEGIES_V2_COMPLETADO.md`
- `docs/DONE/SERVIDORES_INICIADOS.md`
- `docs/DONE/ANALISIS_MIGRACION_STRATEGIES.md`
- `docs/DONE/strategy.md` (reemplazado por nueva arquitectura)
- `frontend/FRONTEND_COMPLETE_REFACTOR.md`
- `frontend/FRONTEND_UX_FIXES_SUMMARY.md`
- `frontend/MIGRATION_SHADCN.md`
- `frontend/UX_PREMIUM_CHANGELOG.md`

### Meta-documentación
- `docs/PENDING/LIMPIEZA_DOCUMENTOS.md`
- `docs/PENDING/README.md`
- `docs/PENDING/RESUMEN_ESTADO_PENDIENTES.md`

### Duplicados
- `VALIDACION_REGLAS_TRADING.md` (raíz) - duplicado de `GENERAL_EXPLANATIONS/VALIDACION_REGLAS_TRADING.md`

---

## ⚠️ Documentación Faltante Crítica

### Para un Sistema de Trading en Producción

1. **Risk Management**
   - ❌ **Falta**: Documentación de límites de exposición por defecto
   - ❌ **Falta**: Procedimiento de emergencia para detener trading
   - ❌ **Falta**: Documentación de circuit breakers y umbrales

2. **Operations**
   - ❌ **Falta**: Runbook de incidentes comunes
   - ❌ **Falta**: Procedimiento de rollback
   - ❌ **Falta**: Checklist pre-deployment

3. **Infrastructure**
   - ❌ **Falta**: Documentación de deployment en producción
   - ❌ **Falta**: Configuración de alta disponibilidad
   - ❌ **Falta**: Backup y recovery procedures

4. **Compliance**
   - ❌ **Falta**: Notas legales sobre trading automatizado
   - ❌ **Falta**: Política de retención de datos
   - ❌ **Falta**: Procedimientos de auditoría

5. **Testing**
   - ❌ **Falta**: Guía de backtesting
   - ❌ **Falta**: Procedimientos de testing en producción (paper trading)

---

## 📝 Próximos Pasos

1. ✅ **Inventario completado** (este documento)
2. ✅ **Aprobación de estructura** (estructura implementada)
3. ✅ **Reorganización de archivos** (estructura creada, archivos consolidados)
4. ✅ **Reescritura de documentación clave** (production-grade completada)
5. ✅ **Creación de documentación faltante** (archivos críticos creados)
6. ⏳ **Actualización de README.md principal** (en progreso)
7. ⏳ **Eliminación de archivos obsoletos** (pendiente limpieza final)

---

## 🔍 Notas Adicionales

### Archivos que Requieren Decisión

1. **`docs/DONE/tech_view.md`**: Muy largo (1800+ líneas). ¿Dividir o consolidar?
2. **`docs/PENDING/`**: Muchos archivos pendientes. ¿Mantener o archivar?
3. **`frontend/` docs**: ¿Crear `docs/frontend/` o mantener en `frontend/`?

### Prioridades

**Alta Prioridad (Producción Crítica)**:
- Risk management documentation
- Kill switch procedures
- Deployment procedures
- Incident response

**Media Prioridad (Operaciones)**:
- Runbook operativo
- Troubleshooting guide
- Monitoring setup

**Baja Prioridad (Mejoras)**:
- Research roadmap
- ADR decisions
- Frontend documentation

---

**Última actualización**: 2025-01-XX

---

## ✅ Estado de Reorganización

### Completado

- ✅ Estructura de carpetas creada (architecture, strategies, infrastructure, risk, backtesting, operations, compliance, research, onboarding, exchange, security, adr)
- ✅ Archivos críticos consolidados:
  - `architecture/system-overview.md` - Consolidado
  - `architecture/data-flow.md` - Consolidado
  - `architecture/execution-engine.md` - Consolidado
  - `infrastructure/secrets.md` - Consolidado
  - `infrastructure/monitoring.md` - Consolidado
  - `risk/controls.md` - Consolidado
  - `risk/kill-switch.md` - Consolidado
  - `operations/runbook.md` - Consolidado
  - `backtesting/data-replay.md` - Consolidado
  - `onboarding/quickstart.md` - Consolidado
- ✅ `docs/README.md` actualizado con índice completo

### Pendiente de Limpieza

- ⏳ Archivos en `DONE/` que ya fueron consolidados (mover a `_archive/`)
- ⏳ Archivos en `GENERAL_EXPLANATIONS/` que ya fueron consolidados (mover a `_archive/`)
- ⏳ Archivos en `PENDING/` que no se consolidaron (evaluar y archivar)
- ⏳ Archivos históricos obsoletos (eliminar según lista)


