# PolyLiquidity Desk - Contexto CTO

**Propósito**: Documento de referencia para GPT actuando como CTO del proyecto  
**Última actualización**: 2025-01-XX

---

## 📑 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Principios Fundamentales](#principios-fundamentales)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Stack Tecnológico](#stack-tecnológico)
5. [Estado del Proyecto](#estado-del-proyecto)
6. [Decisiones Clave](#decisiones-clave)
7. [Guía de Decisiones](#guía-de-decisiones)

---

## 🎯 Resumen Ejecutivo

### ¿Qué es PolyLiquidity Desk?

Sistema de trading algorítmico automatizado para **Polymarket** que detecta oportunidades cuando eventos del mundo real (deportes) terminan antes de que el mercado se resuelva.

**Objetivo**: Capital 100k-200k+ EUR | **Venue**: Polymarket (fijo) | **Estrategia**: Near-resolution liquidity + pre-settlement arbitrage

### Características Clave

| Característica | Descripción |
|---------------|------------|
| **Arquitectura** | Modular, desacoplada, observable, testeable |
| **Estrategias** | Grafos JSON declarativos (no código hardcodeado) |
| **Riesgo** | 8 controles configurables + circuit breakers |
| **Observabilidad** | Métricas, logs estructurados, historical replay |
| **Operación** | Live Control, Runtime Supervisor, fail-safes automáticos |

### Flujo Principal

```
Scanner → Event Mapping → Checker → Event Watch → Strategy → Risk → Execution → Polymarket
```

---

## 🔒 Principios Fundamentales

**⚠️ ESTOS PRINCIPIOS SON NO NEGOCIABLES - Cualquier decisión que los viole es incorrecta**

| # | Principio | Explicación |
|---|-----------|-------------|
| 1 | **Strategy es la entidad raíz** | No markets o events |
| 2 | **Event es la unidad de ejecución atómica** | No el market |
| 3 | **Estrategias NO llaman APIs directamente** | Solo leen State Cache |
| 4 | **Fuentes de datos externas configurables** | Desde DB/frontend |
| 5 | **No nombres hardcodeados** | Todo configurable |
| 6 | **Solo venue de ejecución fijo** | Polymarket |
| 7 | **Estrategias declarativas** | JSON, no código Python |
| 8 | **ExecutionPlan inmutable** | Separa decisión de ejecución |
| 9 | **Execution Graph para operar** | Maneja multi-leg, reintentos, compensación |
| 10 | **Triggers explícitos** | No "evaluar siempre" |

---

## 🏗️ Arquitectura del Sistema

### Componentes Principales

| Componente | Responsabilidad | Path |
|------------|----------------|------|
| **Scanner Engine** | Descubrimiento y filtrado de mercados | - |
| **Event Mapping Layer** | Mapeo mercados → eventos reales | - |
| **Checker System** | Verificación estado eventos (APIs externas) | - |
| **Event Watch Engine** | Monitoreo tiempo real con watchers paralelos | - |
| **Strategy Engine** | Grafos declarativos JSON (Decision + Execution) | Hot/Cold |
| **Risk Engine** | Validación riesgo y ajuste tamaños | - |
| **Execution Engine** | Firma EIP-712 y envío órdenes | - |
| **Runtime Supervisor** | Salud sistema, circuit breakers, fail-safes | - |
| **Metrics & Observability** | Recopilación métricas y alertas | - |
| **Historical Replay** | Registro y replay eventos históricos | - |
| **Live Control** | Visualización y supervisión tiempo real | - |

### Arquitectura de Estrategias (Grafos)

```
┌─────────────────────────────────────────────────────────┐
│                    CONTROL LOOP                          │
│  - Evalúa Strategy Triggers                              │
│  - Dispara Decision Graph (solo si trigger match)       │
│  - Ejecuta Execution Graphs para planes listos           │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│  DECISION GRAPH  │              │  EXECUTION GRAPH │
│  (Hot Path)      │              │  (Cold Path)     │
│  < 50μs          │              │  Async, APIs OK  │
│  Solo lee Cache  │              │  Reintentos OK   │
│  Construye Plan  │              │  Ejecuta Plan    │
└──────────────────┘              └──────────────────┘
        │                                   │
        ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│  STATE CACHE     │              │  EXECUTION PLAN  │
│  - market_state  │              │  (Inmutable)     │
│  - event_state   │              │  - 1 leg (near)  │
│  - external_data │              │  - N legs (sure) │
│  - risk_state    │              └──────────────────┘
└──────────────────┘
```

### Invariantes de Ejecución (CRÍTICOS)

1. ✅ **ExecutionPlan es inmutable después de creación**
2. ✅ **Ningún nodo puede modificar plan después de PLAN_BUILT**
3. ✅ **Transiciones de estado estrictamente controladas**
4. ✅ **TTL de ejecución estrictamente aplicado**
5. ✅ **Execution Graph NO lee datos externos para decisiones**
6. ✅ **Compensación solo reduce exposición, nunca aumenta**
7. ✅ **Hot path NO modifica State Cache**

---

## 💻 Stack Tecnológico

### Backend
- **Python 3.12+** | **FastAPI** | **SQLAlchemy + Alembic** | **PostgreSQL/SQLite**
- **Pytest** | **Asyncio** | **Pydantic** | **Ethereum Libraries** | **py-clob-client**

### Frontend
- **Next.js 14** (App Router) | **TypeScript** | **Tailwind CSS** | **Stack OAuth**

### Operación
- **High-frequency loop** (1-5s) | **Fault-tolerant** | **Monitored & Audited**

---

## 📊 Estado del Proyecto

### Refactorización: ✅ COMPLETA (FASE 0-14)

| Fase | Módulo | Estado |
|------|--------|--------|
| 0 | Testing Infrastructure | ✅ |
| 1 | Wallet Service | ✅ |
| 2 | Metrics & Observability | ✅ |
| 3 | Runtime Supervisor | ✅ |
| 4 | Scanner Engine | ✅ |
| 5 | Event Mapping Layer | ✅ |
| 6 | Checker System | ✅ |
| 7 | Event Watch Engine | ✅ |
| 8 | Strategy Engine | ✅ |
| 9 | Risk Engine | ✅ |
| 10 | Execution Engine | ✅ |
| 11 | Historical Replay | ✅ |
| 12 | Live Control | ✅ |
| 13 | Integración Main Loop | ✅ |
| 14 | Testing Completo | ✅ |

### Testing: ✅ 257 tests unitarios pasando

### Documentación: ✅ Reorganizada y completa

---

## 🎯 Decisiones Clave

### 1. Arquitectura Basada en Grafos
**Decisión**: Estrategias = Grafos JSON declarativos  
**Razón**: Flexibilidad, configurabilidad frontend, múltiples estrategias sin código

### 2. Separación Hot/Cold Path
**Decisión**: Decision Graph (hot) solo lee Cache, Execution Graph (cold) usa APIs  
**Razón**: Latencia < 50μs en decisiones críticas + operaciones asíncronas complejas

### 3. Execution Plans Inmutables
**Decisión**: Plans inmutables después de creación  
**Razón**: Trazabilidad, previene bugs, compensación segura

### 4. State Cache Centralizado
**Decisión**: Un único cache para todo el estado  
**Razón**: Decision Graphs leen sin APIs, Support Graphs actualizan async

### 5. Strategy Triggers Explícitos
**Decisión**: No "evaluar siempre", solo cuando condiciones se cumplen  
**Razón**: Eficiencia, control explícito, previene loops innecesarios

---

## 🎓 Guía de Decisiones

### Prioridades (Orden de Importancia)

1. **🔒 Seguridad y Riesgo** - Siempre primero
2. **🛡️ Confiabilidad** - Robustez y fault-tolerance
3. **👁️ Observabilidad** - Fácil diagnóstico
4. **⚡ Performance** - Latencia crítica (< 50μs Decision Graph)
5. **🔧 Flexibilidad** - Múltiples estrategias sin modificar código

### Restricciones (NO HACER)

- ❌ **NO modificar principios fundamentales** (los 10 son inmutables)
- ❌ **NO hardcodear lógica de estrategia** (todo configurable)
- ❌ **NO llamar APIs desde hot path** (solo State Cache)
- ❌ **NO modificar ExecutionPlans después de creación** (inmutabilidad)

### Métricas de Éxito

| Métrica | Objetivo |
|---------|----------|
| **Uptime** | > 99.9% |
| **Latencia Decision Graph** | < 50μs |
| **Latencia Execution** | < 500ms |
| **Precisión Estrategias** | 100% según configuración |
| **Incidentes Seguridad** | 0 |

### Gestión de Riesgo

| Control | Límite Default |
|---------|----------------|
| Max Market Exposure | 10,000 USDC |
| Max Global Exposure | 50,000 USDC |
| Max Order Size | 5,000 USDC |
| Max Active Markets | 20 |

**Circuit Breakers**: Trading | Checkers | API  
**Fail-Safes**: Automáticos en condiciones críticas

### Seguridad

| Aspecto | Regla |
|--------|-------|
| **Claves Privadas** | ❌ NUNCA en código, ✅ Variables de entorno |
| **Credenciales** | ❌ NUNCA en logs, ✅ Encriptación Fernet (DB) |
| **Validación** | ✅ Todas las entradas validadas |
| **Firma EIP-712** | ✅ Validación completa |

### Configuración Mínima

```bash
# REQUERIDO
STACK_SECRET_SERVER_KEY=sk_live_...
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Para trading real
PRIVATE_KEY=0x...
FUNDER_ADDRESS=0x...
RPC_URL=https://polygon-rpc.com/
CHAIN_ID=137
```

### Rate Limits (Polymarket)

| API | Límite |
|-----|--------|
| Data API | 200 req/10s |
| Trading API | 2400 req/10s |
| Scanner API | 200 req/10s |

---

## 📚 Referencias Rápidas

### Documentación Clave
- **Arquitectura**: `docs/architecture/system-overview.md`
- **Estrategias**: `docs/strategies/README.md`
- **Riesgo**: `docs/risk/controls.md`
- **Execution**: `docs/architecture/execution-engine.md`
- **Operación**: `docs/operations/runbook.md`

### Código Clave
- **Main Loop**: `backend/app/main.py`
- **Strategy Engine**: `backend/app/core/strategy_engine/`
- **Risk Engine**: `backend/app/core/risk_engine/`
- **Execution Engine**: `backend/app/core/execution/`

### Estructura Documentación
```
docs/
├── architecture/    # Arquitectura, flujo, execution
├── strategies/      # Filosofía, ejemplos, tipos
├── infrastructure/  # Deployment, secretos, monitoreo
├── risk/            # Controles, políticas, kill switches
├── exchange/        # Integración Polymarket
├── operations/      # Runbooks, incidentes, troubleshooting
├── backtesting/     # Framework, historical replay
├── research/        # Experimentos, roadmap
├── security/        # Threat model, secretos
├── compliance/      # Legal
└── onboarding/      # Quickstart
```

---

## ⚠️ Consideraciones Críticas

### Seguridad
- Sistema mueve dinero real → Seguridad primero
- Claves privadas nunca expuestas
- Validación exhaustiva de entradas
- Circuit breakers siempre implementados

### Performance
- Latencia crítica: Decision Graph < 50μs
- Rate limiting: Respetar límites APIs
- Caching inteligente: Reducir llamadas API
- Async operations: Usar asyncio para I/O

### Operación
- Monitoreo continuo: Sistema observable siempre
- Fail-safes automáticos: Sistema se protege solo
- Trazabilidad completa: Todas las acciones auditables
- Recuperación automática: Recuperarse de errores cuando sea posible

---

**Este documento debe actualizarse cuando haya cambios significativos en arquitectura, stack, o decisiones estratégicas.**
