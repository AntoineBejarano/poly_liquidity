# Documentación PolyLiquidity

Índice de la documentación alineada con el estado actual del sistema.

---

## Política v2: wallet por usuario (sin CLOB global)

- **[Boot vs Runtime](implementation/BOOT_VS_RUNTIME.md)** — Qué se inicializa en arranque y qué es lazy; garantías (sin CLOB/WS USER en boot, sin PRIVATE_KEY/FUNDER).
- **[Frontend y wallet](implementation/FRONTEND_WALLET_POLICY_V2.md)** — Cómo el frontend maneja 409 WALLET_NOT_CONFIGURED y enlace a Ajustes → Wallets.
- **[Plan refactor wallet](implementation/PLAN_WALLET_SCOPE_REFACTOR.md)** — Alcance del refactor aplicado (estado de implementación).

---

## Arquitectura

- [architecture/system-overview.md](architecture/system-overview.md) — Visión general del sistema
- [architecture/data-flow.md](architecture/data-flow.md) — Flujo de datos e ingestión
- [architecture/execution-engine.md](architecture/execution-engine.md) — Motor de ejecución y estrategias
- [architecture/graph-nodes-reference.md](architecture/graph-nodes-reference.md) — Referencia de nodos de grafos
- [architecture/quorum.md](architecture/quorum.md) — Quorum dinámico
- [architecture/config-driven.md](architecture/config-driven.md) — Arquitectura config-driven

---

## Estrategias

- [strategies/README.md](strategies/README.md) — Filosofía y conceptos
- [strategies/templates.md](strategies/templates.md) — Plantillas
- [strategies/examples/](strategies/examples/) — Ejemplos

---

## Infraestructura

- [infrastructure/secrets.md](infrastructure/secrets.md) — Variables de entorno y secretos (wallet en BD; PRIVATE_KEY/FUNDER ignorados en backend)
- [infrastructure/monitoring.md](infrastructure/monitoring.md) — Métricas y observabilidad
- [infrastructure/RAILWAY_DEPLOY.md](infrastructure/RAILWAY_DEPLOY.md) — Despliegue en Railway

---

## Riesgo

- [risk/controls.md](risk/controls.md) — Controles de riesgo y exposición
- [risk/policy.md](risk/policy.md) — Políticas y parámetros protegidos
- [risk/kill-switch.md](risk/kill-switch.md) — Circuit breakers y fail-safes

---

## Exchange

- [exchange/polymarket-integration.md](exchange/polymarket-integration.md) — Integración Polymarket
- [exchange/order-lifecycle.md](exchange/order-lifecycle.md) — Ciclo de vida de órdenes
- [exchange/failure-modes.md](exchange/failure-modes.md) — Modos de fallo

---

## Operaciones

- [operations/runbook.md](operations/runbook.md) — Procedimientos operativos
- [operations/incident-response.md](operations/incident-response.md) — Respuesta a incidentes
- [operations/release-checklist.md](operations/release-checklist.md) — Checklist de release
- [operations/troubleshooting.md](operations/troubleshooting.md) — Resolución de problemas

---

## Seguridad

- [security/threat-model.md](security/threat-model.md) — Modelo de amenazas
- [security/secrets-handling.md](security/secrets-handling.md) — Manejo de secretos

---

## Otros

- [onboarding/quickstart.md](onboarding/quickstart.md) — Guía de inicio rápido
- [api/markets.md](api/markets.md) — API de mercados
- [backtesting/framework.md](backtesting/framework.md) — Framework de backtesting
- [backtesting/data-replay.md](backtesting/data-replay.md) — Replay de datos históricos
- [research/experiments.md](research/experiments.md) — Experimentos
- [research/roadmap.md](research/roadmap.md) — Roadmap de investigación
- [compliance/legal-notes.md](compliance/legal-notes.md) — Notas legales
- [VERSIONING.md](VERSIONING.md) — Versionado

---

## Histórico

- [_archive/](_archive/) — Documentación antigua o de planes ya ejecutados (solo referencia histórica)
