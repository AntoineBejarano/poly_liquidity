# Plan de Limpieza Final de Documentación

**Fecha**: 2025-01-XX  
**Objetivo**: Alinear toda la documentación con la nueva estructura organizada

---

## ✅ Archivos Ya Movidos a _archive/

- `ESTADO_ACTUAL_BACKEND.md`
- `STRATEGIES.md` (duplicado de raíz)
- `VARIABLES_ENTORNO.md` (duplicado de raíz)

---

## 📦 Archivos a Mover de DONE/ → _archive/

Todos estos archivos ya fueron consolidados en la nueva estructura:

1. `algoritmo_backend.md` → Consolidado en `architecture/system-overview.md`
2. `checker_system.md` → Consolidado en `architecture/data-flow.md`
3. `event_mapping_layer.md` → Consolidado en `architecture/data-flow.md`
4. `event_watch_engine.md` → Consolidado en `architecture/data-flow.md`
5. `execution.md` → Consolidado en `architecture/execution-engine.md`
6. `historical_replay.md` → Consolidado en `backtesting/data-replay.md`
7. `livecontrol.md` → Consolidado en `operations/runbook.md`
8. `metrics_observabilitiy.md` → Consolidado en `infrastructure/monitoring.md`
9. `POLYMARKET_CLIENT_INTEGRATION.md` → Consolidado en `exchange/polymarket-integration.md`
10. `POLYMARKET_WEBSOCKET_INTEGRATION.md` → Consolidado en `exchange/polymarket-integration.md`
11. `risk_engine.md` → Consolidado en `risk/controls.md` y `risk/policy.md`
12. `runtime_supervisor.md` → Consolidado en `risk/kill-switch.md` y `infrastructure/monitoring.md`
13. `scanner.md` → Consolidado en `architecture/data-flow.md`
14. `signatures_trazability.md` → Consolidado en `architecture/execution-engine.md`
15. `wallet_service.md` → Consolidado en `infrastructure/secrets.md`
16. `SCANNER_API_ANALYSIS.md` → Consolidado en `architecture/data-flow.md`
17. `QUORUM_DINAMICO_IMPLEMENTADO.md` → Consolidado en `architecture/quorum.md`
18. `INSTALACION_DEPENDENCIAS.md` → Consolidado en `onboarding/quickstart.md`

**Especiales:**
- `tech_view.md` → Muy largo, mantener en _archive/ para referencia histórica
- `FRONTEND_CONFIG_DECISION_TRACES.md` → Mover a `_triage/` para evaluación

---

## 📦 Archivos a Mover de GENERAL_EXPLANATIONS/ → _archive/

Todos estos archivos ya fueron consolidados:

1. `Executive_Summary.md` → Consolidado en `architecture/system-overview.md`
2. `GUIA_INICIO.md` → Consolidado en `onboarding/quickstart.md`
3. `overall.md` → Consolidado en `architecture/system-overview.md`
4. `strategies_theory.md` → Consolidado en `strategies/README.md`
5. `VALIDACION_REGLAS_TRADING.md` → Consolidado en `risk/policy.md`

---

## 📦 Archivos a Procesar de PENDING/

### Consolidar:
- `PARAMETROS_PROTEGIDOS.md` → Consolidar en `risk/policy.md`
- `DECISION_TRACE_GUIDELINES.md` → Consolidar en `operations/troubleshooting.md`
- `GUIA_PLANTILLAS_ESTRATEGIAS.md` → Mover a `strategies/` o consolidar

### Mover a _triage/:
- `CONFIG_DRIVEN_ARCHITECTURE.md` → Ya consolidado en `architecture/config-driven.md`
- `CONFIG_DRIVEN_SUMMARY.md` → Ya consolidado
- `QUORUM_DINAMICO_REQUISITOS.md` → Ya consolidado en `architecture/quorum.md`
- `QUORUM_SEMANTICA_CORREGIDA.md` → Ya consolidado
- `QUORUM_VIOLACIONES.md` → Ya consolidado

### Mover a research/roadmap.md (consolidar contenido):
- `PLAN_IMPLEMENTACION_INDICADORES_AVANZADOS.md`
- `PLAN_IMPLEMENTACION_SERIES_MARKETS.md`
- `PLAN_MEJORA_LATENCY_Y_UX.md`
- `SERIES_MARKETS.md`
- `PLAN_CARGA_SEPARADA_COMPONENTES.md`

### Eliminar (meta-documentación):
- `LIMPIEZA_DOCUMENTOS.md`
- `README.md` (de PENDING/)
- `RESUMEN_ESTADO_PENDIENTES.md`

### Evaluar (mover a _triage/):
- `ARQUITECTURA_UX_PLATAFORMA_TRADING.md`
- `FRONTEND_API_ENDPOINTS.md`
- `template_estrategy_live_control.html`

---

## 📦 Archivos en Raíz de docs/ a Procesar

### Ya movidos:
- ✅ `STRATEGIES.md` → _archive/
- ✅ `VARIABLES_ENTORNO.md` → _archive/

### Pendientes:
- `BACKEND_ARCHITECTURE_STRATEGIES.md` → Consolidado en `architecture/execution-engine.md` → Mover a _archive/
- `EJEMPLO_ESTRATEGIA_COMPLETA.json` → Ya movido a `strategies/examples/` → Eliminar duplicado

### Meta-documentación (mantener o mover a _archive/):
- `DOCUMENTATION_AUDIT.md` → Mantener (útil para referencia)
- `REORGANIZATION_STATUS.md` → Mantener (útil para referencia)
- `REFACTOR_SUMMARY.md` → Mover a _archive/ (histórico)

---

## 🎯 Resultado Final Esperado

Después de la limpieza:

```
docs/
├── _archive/          # Archivos históricos consolidados
├── _triage/          # Archivos pendientes de evaluación
├── architecture/      # ✅ Organizado
├── strategies/        # ✅ Organizado
├── infrastructure/    # ✅ Organizado
├── risk/              # ✅ Organizado
├── backtesting/       # ✅ Organizado
├── operations/        # ✅ Organizado
├── exchange/          # ✅ Organizado
├── research/          # ✅ Organizado
├── security/          # ✅ Organizado
├── compliance/        # ✅ Organizado
├── onboarding/        # ✅ Organizado
├── adr/               # ✅ Organizado
├── README.md          # ✅ Índice principal
├── DOCUMENTATION_AUDIT.md  # Meta-doc (mantener)
└── REORGANIZATION_STATUS.md # Meta-doc (mantener)
```

**NO debe haber:**
- ❌ Carpetas `DONE/` o `GENERAL_EXPLANATIONS/` (vacías o eliminadas)
- ❌ Archivos `.md` o `.json` sueltos en raíz de `docs/` (excepto meta-docs)
- ❌ Duplicados entre carpetas organizadas y archivos sueltos

---

## 📝 Notas

- Los archivos en `_archive/` se mantienen para referencia histórica
- Los archivos en `_triage/` necesitan evaluación manual
- La meta-documentación (`DOCUMENTATION_AUDIT.md`, `REORGANIZATION_STATUS.md`) se mantiene para referencia del proceso de reorganización

