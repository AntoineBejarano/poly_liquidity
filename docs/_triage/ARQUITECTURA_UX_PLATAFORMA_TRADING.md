# Arquitectura de UX - Plataforma de Trading Algorítmico

**Documento de Diseño UX/Producto**  
**Autor:** Senior UX Architect / Product Designer  
**Fecha:** 2025-01-25  
**Versión:** 1.0

---

## Índice

1. [Visión General](#visión-general)
2. [Estructura de Navegación](#estructura-de-navegación)
3. [Dashboard General (Global Overview)](#dashboard-general-global-overview)
4. [Vista de Control por Estrategia](#vista-de-control-por-estrategia)
5. [Relación Dashboard ↔ Estrategias](#relación-dashboard--estrategias)
6. [Principios de UX Aplicados](#principios-de-ux-aplicados)
7. [Stack Tecnológico y UI Framework](#stack-tecnológico-y-ui-framework)
8. [Suposiciones y Consideraciones](#suposiciones-y-consideraciones)

---

## Visión General

### Contexto del Producto

La plataforma gestiona múltiples estrategias de trading algorítmico que se ejecutan en paralelo, cada una conectándose a fuentes externas (Polymarket, Pinnacle, APIs personalizadas). El usuario principal es un **operador avanzado** que necesita:

- **Visibilidad global** del estado de todas las estrategias
- **Control en tiempo real** sobre cada estrategia individual
- **Métricas de riesgo claras** para tomar decisiones rápidas
- **Detección inmediata** de problemas o anomalías

### Objetivos de UX

1. **Detección de problemas en < 5 segundos** desde el dashboard principal
2. **Control granular** sin perder contexto global
3. **Prevención de errores** mediante confirmaciones y estados claros
4. **Densidad de información** optimizada para operadores profesionales
5. **Navegación fluida** entre vistas agregadas y detalladas

---

## Estructura de Navegación

### Arquitectura de Navegación Principal

```
┌─────────────────────────────────────────────────────────┐
│                    NAVEGACIÓN PRINCIPAL                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Dashboard]  [Estrategias]  [Posiciones]  [Mercados]  │
│                                                          │
│  [Configuración]  [Logs]  [Métricas]  [Risk]           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Jerarquía de Vistas

```
1. Dashboard General (Home)
   ├── Vista agregada de todas las estrategias
   ├── Métricas globales de riesgo
   └── System Health global
   
2. Vista de Estrategia Individual
   ├── Control en tiempo real
   ├── Métricas específicas
   ├── Estado de fuentes externas
   └── Timeline de eventos
   
3. Vistas de Soporte
   ├── Posiciones (todas las estrategias)
   ├── Mercados (todos los mercados activos)
   ├── Logs y Traces (filtrables por estrategia)
   └── Configuración de Sistema
```

### Patrón de Navegación: "Overview → Detail → Action"

1. **Overview (Dashboard)**: El usuario identifica qué estrategia requiere atención
2. **Detail (Vista de Estrategia)**: El usuario analiza el estado específico
3. **Action (Control)**: El usuario toma acción (pausar, ajustar, etc.)

**Principio:** Cada nivel debe permitir navegar al siguiente sin perder contexto.

---

## Dashboard General (Global Overview)

### Propósito

El Dashboard General es la **vista de entrada** y el **centro de comando** de la plataforma. Debe permitir al operador:

- Identificar problemas o riesgos en **segundos**
- Entender el estado global del sistema **de un vistazo**
- Navegar rápidamente a estrategias específicas cuando sea necesario

### Layout y Estructura

```
┌─────────────────────────────────────────────────────────────────────┐
│  DASHBOARD GENERAL                                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  MÉTRICAS GLOBALES (KPI Cards - Top Row)                     │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │ │
│  │  │ PnL  │ │ Exp. │ │ Cap. │ │ Draw│ │ Sist.│              │ │
│  │  │ Agreg│ │ Total│ │ Disp.│ │ down│ │ Health│              │ │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  ALERTAS CRÍTICAS (Banner - Si hay alertas)                  │ │
│  │  ⚠️ [Alerta 1] [Alerta 2] [Alerta 3]                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  TABLA DE ESTRATEGIAS (Main Content)                         │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │ Estado │ Nombre    │ PnL   │ Exp.  │ Riesgo │ Health │ │ │
│  │  ├─────────────────────────────────────────────────────────┤ │ │
│  │  │ 🟢 Run│ Strategy1 │ +$500 │ $2.5K │ 🟡 75% │ 🟢 OK  │ │ │
│  │  │ 🔴 Err│ Strategy2 │ -$200 │ $0    │ ⚪ 0%  │ 🔴 Fail │ │ │
│  │  │ ⚪ Paus│ Strategy3 │ $0    │ $1.2K │ 🟢 45% │ 🟡 Degr │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  SYSTEM HEALTH (Sidebar Right)                              │ │
│  │  ┌───────────────────────────────────────────────────────┐ │ │
│  │  │ Conexiones Externas                                   │ │ │
│  │  │ • Polymarket: 🟢 OK (lat: 45ms)                       │ │ │
│  │  │ • Pinnacle: 🟡 Degraded (lat: 250ms)                  │ │ │
│  │  │ • Custom API: 🔴 Error                                │ │ │
│  │  └───────────────────────────────────────────────────────┘ │ │
│  │  ┌───────────────────────────────────────────────────────┐ │ │
│  │  │ Eventos Recientes (Timeline)                          │ │ │
│  │  │ • 2m ago: Strategy1 ejecutó orden                    │ │ │
│  │  │ • 5m ago: Strategy2 error de conexión                │ │ │
│  │  └───────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Sección 1: Métricas Globales (KPI Cards)

**Ubicación:** Fila superior del dashboard  
**Actualización:** Tiempo real (WebSocket)  
**Diseño:** Cards compactos con valores grandes y tendencias

#### Card 1: PnL Agregado
```
┌─────────────────┐
│ PnL Total       │
│                 │
│  +$1,234.56     │ ← Valor grande, destacado
│  ↑ +2.3% (24h)  │ ← Tendencia pequeña
│                 │
│  Realizado: $800│ ← Desglose pequeño
│  No Realizado:  │
│  $434.56        │
└─────────────────┘
```

**Información:**
- PnL total agregado (realizado + no realizado)
- Tendencia (24h, 7d)
- Desglose: realizado vs no realizado
- Color: Verde (positivo), Rojo (negativo), Gris (neutral)

#### Card 2: Exposición Total
```
┌─────────────────┐
│ Exposición      │
│                 │
│  $15,234 /      │
│  $50,000        │
│                 │
│  ████████░░ 30% │ ← Barra de progreso
│                 │
│  🟢 Seguro       │ ← Estado de riesgo
└─────────────────┘
```

**Información:**
- Exposición actual vs límite máximo
- Porcentaje visual (barra de progreso)
- Estado de riesgo: 🟢 Seguro, 🟡 Atención, 🔴 Crítico
- Click → Navega a vista de riesgo detallada

#### Card 3: Capital Disponible
```
┌─────────────────┐
│ Capital         │
│                 │
│  $34,765.44     │
│                 │
│  Comprometido:  │
│  $15,234.56     │
│                 │
│  Disponible:    │
│  $19,530.88     │
└─────────────────┘
```

**Información:**
- Capital total (equity)
- Capital comprometido (en posiciones)
- Capital disponible (para nuevas operaciones)
- Porcentaje de utilización

#### Card 4: Drawdown Global
```
┌─────────────────┐
│ Drawdown        │
│                 │
│  -$2,345.67     │
│  -5.2%          │
│                 │
│  Máximo:        │
│  -$5,000 (-10%) │
│                 │
│  Desde: 2d ago  │
└─────────────────┘
```

**Información:**
- Drawdown actual (absoluto y porcentual)
- Drawdown máximo histórico
- Tiempo desde el peak
- Color según severidad

#### Card 5: System Health Global
```
┌─────────────────┐
│ System Health   │
│                 │
│  🟢 HEALTHY     │ ← Estado general
│                 │
│  Estrategias:   │
│  8/10 activas   │
│                 │
│  Conexiones:    │
│  2/3 OK         │
│                 │
│  ⚠️ 1 alerta    │
└─────────────────┘
```

**Información:**
- Estado general del sistema (🟢 HEALTHY, 🟡 DEGRADED, 🔴 CRITICAL)
- Estrategias activas vs totales
- Conexiones externas OK vs totales
- Contador de alertas críticas
- Click → Navega a vista de System Health detallada

### Sección 2: Alertas Críticas (Banner)

**Ubicación:** Debajo de KPI Cards, solo visible si hay alertas  
**Diseño:** Banner destacado con colores según severidad

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ ALERTAS CRÍTICAS                                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🔴 [Strategy2] Error de conexión a Pinnacle            │
│     [Ver detalles] [Pausar estrategia]                  │
│                                                          │
│  🟡 [Strategy5] Exposición al 85% del límite           │
│     [Ver detalles] [Ajustar límites]                    │
│                                                          │
│  🟡 [System] Latencia alta en Polymarket (250ms)        │
│     [Ver detalles]                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Comportamiento:**
- Solo se muestra si hay alertas activas
- Ordenadas por severidad (🔴 Crítico → 🟡 Advertencia)
- Cada alerta es clickeable → Navega a la estrategia/sistema responsable
- Acciones rápidas disponibles (pausar, ajustar, etc.)

### Sección 3: Tabla de Estrategias (Contenido Principal)

**Ubicación:** Centro del dashboard, área principal  
**Diseño:** Tabla densa con información clave, ordenable y filtrable

#### Columnas de la Tabla

| Columna | Descripción | Formato |
|---------|-------------|---------|
| **Estado** | Estado actual de ejecución | Badge con icono: 🟢 Running, ⚪ Paused, 🔴 Error, 🟡 Degraded |
| **Nombre** | Nombre de la estrategia | Texto clickeable → Navega a vista detallada |
| **PnL** | PnL de la estrategia | Moneda con color: Verde (+), Rojo (-), Gris (0) |
| **Exposición** | Exposición actual | Moneda + porcentaje del límite |
| **Riesgo** | Nivel de riesgo | Barra de progreso + color: 🟢 <50%, 🟡 50-80%, 🔴 >80% |
| **Health** | Estado de salud | Badge: 🟢 OK, 🟡 Degraded, 🔴 Error |
| **Última Acción** | Última operación/evento | Timestamp relativo (ej: "2m ago") |
| **Acciones** | Controles rápidos | Botones: Play/Pause/Stop |

#### Ejemplo de Fila

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🟢 Running │ Near-Resolution LP │ +$234.56 │ $2,500 (50%) │ 🟡 75% │ 🟢 OK │ 2m ago │ [⏸️] [⏹️] │
└──────────────────────────────────────────────────────────────────────────┘
```

**Interacciones:**
- **Click en nombre** → Navega a vista detallada de la estrategia
- **Click en PnL** → Muestra tooltip con desglose (realizado/no realizado)
- **Click en Exposición** → Muestra tooltip con posiciones activas
- **Click en Riesgo** → Navega a vista de riesgo de la estrategia
- **Hover en Health** → Muestra detalles de salud (latencias, errores, etc.)
- **Botones de acción** → Control directo (pausar, detener)

#### Filtros y Ordenamiento

**Filtros disponibles:**
- Estado (Running, Paused, Error, Degraded)
- Health (OK, Degraded, Error)
- Riesgo (Bajo, Medio, Alto)
- Tags (si aplica)

**Ordenamiento:**
- Por defecto: Por PnL (descendente)
- Alternativas: Por exposición, por riesgo, por nombre, por última acción

### Sección 4: System Health (Sidebar Derecha)

**Ubicación:** Columna derecha del dashboard  
**Diseño:** Panel compacto con información de sistema

#### Subsección 4.1: Conexiones Externas

```
┌─────────────────────────────────────┐
│ Conexiones Externas                │
├─────────────────────────────────────┤
│                                     │
│ Polymarket                          │
│ 🟢 OK                               │
│ Latencia: 45ms (p95: 120ms)         │
│ Última actualización: 2s ago       │
│                                     │
│ Pinnacle                            │
│ 🟡 Degraded                         │
│ Latencia: 250ms (p95: 450ms)       │
│ Última actualización: 15s ago       │
│ [Reconectar]                        │
│                                     │
│ Custom API (Sports)                 │
│ 🔴 Error                            │
│ Error: Connection timeout           │
│ Última actualización: 5m ago       │
│ [Reconectar] [Ver logs]            │
│                                     │
└─────────────────────────────────────┘
```

**Información por conexión:**
- Estado (🟢 OK, 🟡 Degraded, 🔴 Error)
- Latencia actual y percentiles (p95, p99)
- Última actualización (timestamp relativo)
- Acciones rápidas (reconectar, ver logs)

#### Subsección 4.2: Eventos Recientes (Timeline)

```
┌─────────────────────────────────────┐
│ Eventos Recientes                   │
├─────────────────────────────────────┤
│                                     │
│ 2m ago                              │
│ [Strategy1] Ejecutó orden           │
│ $500 @ 0.95                         │
│                                     │
│ 5m ago                              │
│ [Strategy2] Error de conexión       │
│ Pinnacle API timeout                │
│                                     │
│ 8m ago                              │
│ [System] Exposición global al 75%   │
│                                     │
│ 12m ago                             │
│ [Strategy3] Pausada manualmente     │
│                                     │
│ [Ver todos los eventos →]           │
│                                     │
└─────────────────────────────────────┘
```

**Información:**
- Timeline de eventos recientes (últimos 30 minutos)
- Agrupado por estrategia o sistema
- Click en evento → Navega a contexto relevante
- Link "Ver todos" → Navega a vista de logs completa

### Principios de Diseño del Dashboard

1. **Densidad de Información:** Máxima información visible sin scroll
2. **Jerarquía Visual:** Lo más crítico (alertas, errores) es lo más visible
3. **Color Semántico:** Verde (OK), Amarillo (Atención), Rojo (Crítico)
4. **Actualización en Tiempo Real:** WebSocket para actualizaciones sin refresh
5. **Navegación Directa:** Cada elemento clickeable lleva al detalle relevante

---

## Vista de Control por Estrategia

### Propósito

La Vista de Control por Estrategia es la **vista operativa detallada** de una estrategia individual. Permite al operador:

- **Controlar** la ejecución de la estrategia (iniciar, pausar, detener)
- **Monitorear** el estado en tiempo real
- **Diagnosticar** problemas específicos
- **Ajustar** parámetros críticos (si el rol lo permite)

### Layout y Estructura

```
┌─────────────────────────────────────────────────────────────────────┐
│  VISTA DE ESTRATEGIA: Near-Resolution Liquidity Provider            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  HEADER: Control y Estado                                    │ │
│  │  [⏸️ Pausar] [⏹️ Detener] [⚙️ Config]  Estado: 🟢 Running    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  MÉTRICAS DE ESTRATEGIA (KPI Cards)                          │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │ │
│  │  │ PnL  │ │ Exp. │ │ Int. │ │ Win  │ │ Last │              │ │
│  │  │      │ │      │ │ Exec.│ │ Rate │ │ Act. │              │ │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  INFORMACIÓN DE ESTRATEGIA                                   │ │
│  │  ┌──────────────────────┐ ┌──────────────────────────────┐ │ │
│  │  │ Configuración        │ │ Mercados Activos             │ │ │
│  │  │ • Tipo: Liquidity LP  │ │ • Event A (2 posiciones)     │ │ │
│  │  │ • Eventos: 5         │ │ • Event B (1 posición)       │ │ │
│  │  │ • Risk Config: ...   │ │ • Event C (0 posiciones)     │ │ │
│  │  └──────────────────────┘ └──────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  POSICIONES ABIERTAS                                        │ │
│  │  [Tabla de posiciones activas]                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  SYSTEM HEALTH ESPECÍFICO                                    │ │
│  │  ┌──────────────────────┐ ┌──────────────────────────────┐ │ │
│  │  │ Fuentes Externas     │ │ Timeline de Eventos          │ │ │
│  │  │ • Polymarket: 🟢 OK  │ │ • 2m ago: Orden ejecutada    │ │ │
│  │  │ • Sports API: 🟡 Deg. │ │ • 5m ago: Support Graph OK   │ │ │
│  │  └──────────────────────┘ └──────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  ÚLTIMAS OPERACIONES / INTENTS                               │ │
│  │  [Tabla de intents recientes]                                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Sección 1: Header de Control

**Ubicación:** Parte superior de la vista  
**Diseño:** Barra horizontal con controles y estado

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Volver al Dashboard                                              │
│                                                                     │
│  Near-Resolution Liquidity Provider                                 │
│  Descripción: Provee liquidez cerca de la resolución...           │
│                                                                     │
│  Estado: 🟢 Running                    Última actualización: 2s ago│
│                                                                     │
│  [⏸️ Pausar] [⏹️ Detener] [⚙️ Configurar] [📊 Métricas] [📝 Logs] │
└─────────────────────────────────────────────────────────────────────┘
```

**Controles:**
- **Pausar:** Pausa temporalmente la estrategia (mantiene estado)
- **Detener:** Detiene completamente la estrategia (requiere confirmación)
- **Configurar:** Abre modal de configuración (si el rol lo permite)
- **Métricas:** Navega a vista de métricas históricas
- **Logs:** Navega a vista de logs filtrados por esta estrategia

**Confirmaciones:**
- **Pausar:** Confirmación simple (1 click)
- **Detener:** Confirmación con advertencia (2 clicks, requiere escribir nombre de estrategia)

### Sección 2: Métricas de Estrategia (KPI Cards)

**Ubicación:** Debajo del header  
**Diseño:** Cards similares al dashboard, pero específicos de la estrategia

#### Card 1: PnL de Estrategia
```
┌─────────────────┐
│ PnL             │
│                 │
│  +$234.56       │
│  ↑ +1.2% (24h)  │
│                 │
│  Realizado:     │
│  $150.00        │
│  No Realizado:  │
│  $84.56         │
└─────────────────┘
```

#### Card 2: Exposición de Estrategia
```
┌─────────────────┐
│ Exposición      │
│                 │
│  $2,500 /       │
│  $5,000         │
│                 │
│  █████░░░░ 50%  │
│                 │
│  🟢 Seguro       │
└─────────────────┘
```

#### Card 3: Intents Ejecutados
```
┌─────────────────┐
│ Intents         │
│                 │
│  45 ejecutados  │
│  (24h)          │
│                 │
│  Aprobados: 42  │
│  Rechazados: 3  │
│                 │
│  Tasa: 93%      │
└─────────────────┘
```

#### Card 4: Win Rate
```
┌─────────────────┐
│ Win Rate        │
│                 │
│  68%            │
│                 │
│  Ganadores: 28  │
│  Perdedores: 13 │
│                 │
│  Avg Profit:    │
│  +$8.50         │
└─────────────────┘
```

#### Card 5: Última Acción
```
┌─────────────────┐
│ Última Acción   │
│                 │
│  2 minutos ago  │
│                 │
│  Orden ejecutada│
│  $500 @ 0.95    │
│                 │
│  [Ver detalles]│
└─────────────────┘
```

### Sección 3: Información de Estrategia

**Ubicación:** Debajo de KPI Cards  
**Diseño:** Dos columnas con información contextual

#### Columna Izquierda: Configuración

```
┌─────────────────────────────────────┐
│ Configuración                       │
├─────────────────────────────────────┤
│                                     │
│ Tipo: Near-Resolution LP            │
│                                     │
│ Eventos Asignados: 5                │
│ • Event A (ACTIVE)                  │
│ • Event B (ACTIVE)                  │
│ • Event C (UPCOMING)                │
│ • Event D (FINISHED)                │
│ • Event E (ACTIVE)                  │
│                                     │
│ Risk Config:                        │
│ • Max Exposure: $5,000              │
│ • Max Order Size: $1,000            │
│ • Max Drawdown: -10%                │
│                                     │
│ Control Loop:                       │
│ • Interval: 10s                     │
│ • Last Execution: 2s ago            │
│                                     │
│ [Editar Configuración]              │
│                                     │
└─────────────────────────────────────┘
```

#### Columna Derecha: Mercados Activos

```
┌─────────────────────────────────────┐
│ Mercados Activos                    │
├─────────────────────────────────────┤
│                                     │
│ Event A - Market XYZ                │
│ 🟢 ACTIVE                           │
│ • Posiciones: 2                     │
│ • Exposición: $1,200                │
│ • Última operación: 5m ago          │
│ [Ver detalles →]                    │
│                                     │
│ Event B - Market ABC                │
│ 🟢 ACTIVE                           │
│ • Posiciones: 1                     │
│ • Exposición: $800                  │
│ • Última operación: 12m ago         │
│ [Ver detalles →]                    │
│                                     │
│ Event C - Market DEF                │
│ ⚪ UPCOMING                         │
│ • Posiciones: 0                     │
│ • Esperando inicio                  │
│ [Ver detalles →]                    │
│                                     │
└─────────────────────────────────────┘
```

### Sección 4: Posiciones Abiertas

**Ubicación:** Debajo de información de estrategia  
**Diseño:** Tabla densa con posiciones activas

```
┌─────────────────────────────────────────────────────────────────────┐
│ Posiciones Abiertas                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Evento      │ Mercado    │ Tamaño │ Precio Avg │ PnL    │ Estado   │
├─────────────────────────────────────────────────────────────────────┤
│ Event A     │ Market XYZ │ $500   │ 0.95       │ +$25   │ 🟢 Open  │
│ Event A     │ Market XYZ │ $700   │ 0.94       │ +$42   │ 🟢 Open  │
│ Event B     │ Market ABC │ $800   │ 0.92       │ -$16   │ 🟢 Open  │
└─────────────────────────────────────────────────────────────────────┘
```

**Información:**
- Evento y mercado asociado
- Tamaño de posición
- Precio promedio de entrada
- PnL no realizado
- Estado (Open, Pending Close, etc.)
- Click en fila → Navega a vista de posición detallada

### Sección 5: System Health Específico

**Ubicación:** Debajo de posiciones  
**Diseño:** Dos columnas con salud del sistema para esta estrategia

#### Columna Izquierda: Fuentes Externas

```
┌─────────────────────────────────────┐
│ Fuentes Externas                    │
├─────────────────────────────────────┤
│                                     │
│ Polymarket (Ejecución)              │
│ 🟢 OK                               │
│ Latencia: 45ms (p95: 120ms)         │
│ Última orden: 2m ago                │
│                                     │
│ Sports API (Confirmación)           │
│ 🟡 Degraded                          │
│ Latencia: 250ms (p95: 450ms)       │
│ Última actualización: 15s ago       │
│ [Reconectar]                        │
│                                     │
│ Support Graph: confirm_event_result │
│ 🟢 OK                               │
│ Última ejecución: 10s ago           │
│                                     │
└─────────────────────────────────────┘
```

**Información:**
- Estado de cada fuente externa usada por la estrategia
- Latencia y percentiles
- Última actividad
- Acciones rápidas (reconectar, ver logs)

#### Columna Derecha: Timeline de Eventos

```
┌─────────────────────────────────────┐
│ Timeline de Eventos                 │
├─────────────────────────────────────┤
│                                     │
│ 2m ago                              │
│ [Execution] Orden ejecutada          │
│ $500 @ 0.95 en Event A              │
│ [Ver trace →]                       │
│                                     │
│ 5m ago                              │
│ [Support Graph] confirm_event_result│
│ Ejecutado correctamente             │
│ [Ver trace →]                       │
│                                     │
│ 8m ago                              │
│ [Decision Graph] Intent generado    │
│ Aprobado por Risk Engine            │
│ [Ver trace →]                       │
│                                     │
│ 12m ago                             │
│ [Warning] Latencia alta en Sports   │
│ API (250ms)                         │
│                                     │
│ [Ver todos los eventos →]           │
│                                     │
└─────────────────────────────────────┘
```

**Información:**
- Timeline de eventos específicos de la estrategia
- Tipos: Execution, Support Graph, Decision Graph, Warnings, Errors
- Click en evento → Navega a trace/log detallado
- Link "Ver todos" → Navega a vista de logs filtrada

### Sección 6: Últimas Operaciones / Intents

**Ubicación:** Parte inferior de la vista  
**Diseño:** Tabla con intents recientes

```
┌─────────────────────────────────────────────────────────────────────┐
│ Últimas Operaciones / Intents                                       │
├─────────────────────────────────────────────────────────────────────┤
│ Timestamp │ Evento │ Acción      │ Estado    │ Resultado            │
├─────────────────────────────────────────────────────────────────────┤
│ 2m ago    │ Event A│ BUY $500    │ ✅ Exec   │ Orden #12345         │
│ 8m ago    │ Event B│ BUY $800    │ ✅ Exec   │ Orden #12344         │
│ 15m ago   │ Event A│ BUY $700    │ ✅ Exec   │ Orden #12343         │
│ 20m ago   │ Event C│ BUY $300    │ ❌ Reject │ Risk: Max exposure   │
│ 25m ago   │ Event A│ BUY $500    │ ✅ Exec   │ Orden #12342         │
└─────────────────────────────────────────────────────────────────────┘
```

**Información:**
- Timestamp relativo
- Evento asociado
- Acción (BUY/SELL) y tamaño
- Estado (Ejecutado, Rechazado, Pendiente)
- Resultado (ID de orden, razón de rechazo)
- Click en fila → Navega a intent/trace detallado

### Principios de Diseño de la Vista de Estrategia

1. **Control Inmediato:** Botones de acción siempre visibles y accesibles
2. **Contexto Completo:** Toda la información relevante en una sola vista
3. **Diagnóstico Rápido:** System Health y Timeline permiten identificar problemas
4. **Navegación Profunda:** Cada elemento clickeable lleva a más detalle
5. **Prevención de Errores:** Confirmaciones para acciones destructivas

---

## Relación Dashboard ↔ Estrategias

### Flujo de Navegación

```
Dashboard General
    │
    ├─→ Click en nombre de estrategia
    │   └─→ Vista de Estrategia Individual
    │
    ├─→ Click en métrica (PnL, Exposición, Riesgo)
    │   └─→ Vista de Estrategia Individual (scroll a sección relevante)
    │
    ├─→ Click en alerta
    │   └─→ Vista de Estrategia Individual (scroll a System Health)
    │
    └─→ Click en acción rápida (Pausar, Detener)
        └─→ Confirmación → Acción ejecutada → Dashboard actualizado
```

### Drill-Down Pattern

**Principio:** Cada nivel de agregación debe permitir "drill-down" al detalle.

1. **Dashboard:** Vista agregada de todas las estrategias
2. **Estrategia:** Vista detallada de una estrategia
3. **Evento/Posición:** Vista detallada de un evento o posición específica
4. **Trace/Log:** Vista detallada de una ejecución o log específico

### Breadcrumbs y Navegación

```
Dashboard > Near-Resolution LP > Event A > Position #12345
```

**Breadcrumbs:**
- Siempre visibles en la parte superior
- Cada nivel es clickeable para volver atrás
- Muestra el contexto completo de navegación

### Actualización Sincronizada

**Principio:** Los cambios en una vista deben reflejarse en todas las vistas relacionadas.

- Si se pausa una estrategia desde el Dashboard → La vista de estrategia se actualiza automáticamente
- Si se pausa desde la vista de estrategia → El Dashboard se actualiza automáticamente
- WebSocket mantiene sincronización en tiempo real

### Highlighting y Focus

**Principio:** Cuando se navega desde el Dashboard a una estrategia, la información relevante debe estar destacada.

- Si se hace click en una alerta → La vista de estrategia se abre con la alerta destacada
- Si se hace click en una métrica → La vista de estrategia se abre con esa métrica en foco
- Scroll automático a la sección relevante

---

## Principios de UX Aplicados

### 1. Claridad y Densidad de Información

**Objetivo:** Máxima información visible sin saturación.

**Aplicación:**
- Uso de iconos semánticos (🟢 🟡 🔴) para estados
- Tipografía jerárquica (valores grandes para KPIs, texto pequeño para detalles)
- Espaciado consistente y respiración visual
- Tablas densas pero legibles (para operadores profesionales)

### 2. Prevención de Errores

**Objetivo:** Evitar acciones destructivas accidentales.

**Aplicación:**
- Confirmaciones para acciones críticas (detener estrategia, cambiar a modo LIVE)
- Estados claros y visibles (modo de ejecución siempre visible)
- Deshabilitación de controles cuando no aplican
- Advertencias visuales antes de acciones riesgosas

### 3. Feedback Inmediato

**Objetivo:** El usuario debe saber inmediatamente el resultado de sus acciones.

**Aplicación:**
- Actualización en tiempo real vía WebSocket
- Indicadores de carga para acciones asíncronas
- Notificaciones toast para acciones completadas
- Estados visuales claros (spinners, badges, colores)

### 4. Jerarquía de Información

**Objetivo:** Lo más crítico es lo más visible.

**Aplicación:**
- Alertas críticas en la parte superior
- Estados de error destacados con color rojo
- Métricas clave en cards grandes
- Información secundaria en tooltips o secciones colapsables

### 5. Navegación Intuitiva

**Objetivo:** El usuario debe poder navegar sin pensar.

**Aplicación:**
- Breadcrumbs siempre visibles
- Links claros y descriptivos
- Botones de acción con iconos y texto
- Navegación contextual (cada elemento clickeable lleva al detalle relevante)

### 6. Consistencia Visual

**Objetivo:** Misma información, mismo formato en todas las vistas.

**Aplicación:**
- Mismo formato de moneda en todas partes
- Mismo formato de timestamps (relativos: "2m ago")
- Mismos colores para estados (🟢 OK, 🟡 Atención, 🔴 Crítico)
- Mismos iconos para acciones (⏸️ Pausar, ⏹️ Detener)

### 7. Responsive y Adaptable

**Objetivo:** Funciona en diferentes tamaños de pantalla (aunque optimizado para desktop).

**Aplicación:**
- Layout flexible que se adapta a diferentes anchos
- Tablas con scroll horizontal en pantallas pequeñas
- Sidebars colapsables en pantallas medianas
- Priorización de información crítica en móviles (si aplica)

---

## Stack Tecnológico y UI Framework

### Framework de UI: shadcn/ui

**Requisito:** Todos los elementos de UI deben implementarse utilizando **shadcn/ui**.

#### ¿Qué es shadcn/ui?

shadcn/ui es una biblioteca de componentes UI construida sobre:
- **Radix UI:** Componentes accesibles y sin estilos
- **Tailwind CSS:** Utilidades de estilos
- **Framer Motion:** Animaciones (opcional)

#### Componentes shadcn/ui a Utilizar

Todos los componentes mencionados en este documento deben implementarse usando los componentes de shadcn/ui:

**Componentes Base:**
- `Button` - Para todos los botones (Pausar, Detener, Configurar, etc.)
- `Card` - Para los KPI Cards del dashboard
- `Table` - Para tablas de estrategias, posiciones, intents
- `Badge` - Para estados (Running, Paused, Error, etc.)
- `Alert` - Para alertas críticas y notificaciones
- `Dialog` - Para modales de confirmación
- `Sonner` (toast) - Para notificaciones de acciones completadas
- `Progress` - Para barras de progreso (exposición, riesgo)
- `Tabs` - Para navegación entre secciones (si aplica)
- `Tooltip` - Para información adicional al hover
- `Skeleton` - Para estados de carga
- `Separator` - Para divisores visuales

**Componentes de Navegación:**
- `Breadcrumb` - Para breadcrumbs de navegación
- `NavigationMenu` - Para menú principal (si aplica)
- `Sidebar` - Para sidebars colapsables

**Componentes de Datos:**
- `DataTable` - Para tablas con ordenamiento y filtros
- `Chart` - Para gráficos de métricas (usando recharts o similar)
- `Timeline` - Para timelines de eventos (puede requerir customización)

**Componentes de Formularios:**
- `Input` - Para inputs de texto
- `Select` - Para dropdowns
- `Switch` - Para toggles
- `Slider` - Para ajustes de valores
- `Checkbox` - Para selección múltiple

**Componentes de Feedback:**
- `AlertDialog` - Para confirmaciones críticas
- `Popover` - Para información contextual
- `DropdownMenu` - Para menús de acciones

#### Ventajas de shadcn/ui

1. **Accesibilidad:** Basado en Radix UI, todos los componentes son accesibles por defecto
2. **Customizable:** Los componentes se copian a tu proyecto, permitiendo modificación completa
3. **Consistencia:** Diseño coherente basado en principios de diseño sólidos
4. **Performance:** Componentes ligeros y optimizados
5. **TypeScript:** Soporte completo de tipos
6. **Tema:** Fácil personalización de temas (dark/light mode)

#### Implementación

**Estructura de Componentes:**

```
components/
├── ui/                    # Componentes shadcn/ui base
│   ├── button.tsx
│   ├── card.tsx
│   ├── table.tsx
│   ├── badge.tsx
│   └── ...
├── dashboard/             # Componentes específicos del dashboard
│   ├── KPICard.tsx        # Usa Card de shadcn/ui
│   ├── StrategyTable.tsx  # Usa Table de shadcn/ui
│   └── AlertBanner.tsx    # Usa Alert de shadcn/ui
├── strategy/              # Componentes específicos de estrategia
│   ├── StrategyHeader.tsx # Usa Button, Badge de shadcn/ui
│   ├── PositionTable.tsx  # Usa Table de shadcn/ui
│   └── EventTimeline.tsx  # Usa componentes base de shadcn/ui
└── shared/                # Componentes compartidos
    ├── StatusBadge.tsx     # Usa Badge de shadcn/ui
    └── ConfirmDialog.tsx   # Usa AlertDialog de shadcn/ui
```

**Ejemplo de Uso:**

```tsx
// KPICard.tsx - Usando Card de shadcn/ui
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

export function KPICard({ title, value, trend, breakdown }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && <div className="text-sm text-muted-foreground">{trend}</div>}
        {breakdown && <div className="text-xs">{breakdown}</div>}
      </CardContent>
    </Card>
  )
}
```

**Tema y Estilos:**

- Utilizar el sistema de tokens de shadcn/ui para colores, espaciado, tipografía
- Personalizar el tema según las necesidades de la plataforma (colores semánticos: 🟢 🟡 🔴)
- Mantener consistencia con los principios de diseño definidos en este documento

#### Componentes Personalizados

Si algún componente no existe en shadcn/ui, se debe:
1. Construir sobre componentes base de shadcn/ui
2. Seguir los mismos patrones de diseño
3. Mantener accesibilidad y consistencia visual
4. Documentar el componente personalizado

**Ejemplo:** Un componente `StatusIndicator` personalizado puede construirse usando `Badge` de shadcn/ui con estilos personalizados.

---

## Suposiciones y Consideraciones

### Suposiciones Técnicas

1. **WebSocket disponible:** Se asume que hay un WebSocket para actualizaciones en tiempo real
2. **Backend preparado:** Se asume que el backend puede proporcionar todas las métricas y datos necesarios
3. **Autenticación y roles:** Se asume un sistema de roles (operador, admin, etc.) que controla permisos
4. **Performance:** Se asume que el backend puede manejar múltiples estrategias sin degradación significativa

### Suposiciones de Usuario

1. **Usuario experto:** El usuario es un operador avanzado familiarizado con trading algorítmico
2. **Múltiples monitores:** El usuario puede tener múltiples monitores (optimizado para desktop)
3. **Tiempo de respuesta crítico:** El usuario necesita información y control en tiempo real
4. **Contexto de uso:** El usuario está monitoreando activamente durante sesiones de trading

### Consideraciones de Implementación

1. **Framework UI:** Todos los componentes deben implementarse usando **shadcn/ui** (ver sección [Stack Tecnológico y UI Framework](#stack-tecnológico-y-ui-framework))
2. **Carga inicial:** El dashboard debe cargar rápidamente (< 2s) incluso con muchas estrategias
3. **Actualizaciones incrementales:** Solo actualizar lo que cambió, no recargar toda la vista
4. **Caché inteligente:** Cachear datos que no cambian frecuentemente (configuración, nombres)
5. **Lazy loading:** Cargar datos detallados solo cuando se necesitan (ej: timeline completo)
6. **Componentes reutilizables:** Construir componentes base sobre shadcn/ui y reutilizarlos en toda la aplicación

### Consideraciones de Escalabilidad

1. **Muchas estrategias:** El dashboard debe funcionar bien con 50+ estrategias (paginación, filtros)
2. **Muchos eventos:** Las tablas deben ser paginadas o virtualizadas
3. **Muchos logs:** Los timelines deben limitarse a eventos recientes (últimos 30 minutos por defecto)
4. **Múltiples usuarios:** Si hay múltiples usuarios, considerar permisos y vistas compartidas

### Consideraciones de Seguridad

1. **Confirmaciones críticas:** Acciones destructivas requieren confirmación explícita
2. **Auditoría:** Todas las acciones deben ser registradas (quién, qué, cuándo)
3. **Modo LIVE:** Cambiar a modo LIVE debe requerir confirmación adicional
4. **Permisos:** Solo usuarios autorizados pueden modificar estrategias activas

---

## Resumen Ejecutivo

### Estructura Propuesta

1. **Dashboard General:** Vista agregada con métricas globales, tabla de estrategias, y system health
2. **Vista de Estrategia:** Vista detallada con control, métricas, posiciones, y system health específico
3. **Navegación fluida:** Drill-down desde agregado a detalle, con breadcrumbs y contexto preservado

### Principios Clave

- **Densidad de información** optimizada para operadores profesionales
- **Prevención de errores** mediante confirmaciones y estados claros
- **Feedback inmediato** vía actualizaciones en tiempo real
- **Jerarquía visual** que prioriza lo crítico
- **Navegación intuitiva** con contexto preservado

### Próximos Pasos

1. **Validación con usuarios:** Revisar la propuesta con operadores reales
2. **Prototipado:** Crear prototipos de alta fidelidad de las vistas clave
3. **Implementación incremental:** Empezar con Dashboard básico, luego agregar funcionalidades
4. **Testing:** Probar con datos reales y múltiples estrategias

---

**Fin del Documento**

