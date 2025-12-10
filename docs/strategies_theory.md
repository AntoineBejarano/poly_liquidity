```markdown
# Polymarket – Estrategias Sistemáticas con Edge Real

Este documento describe **tres estrategias automatizables** que **sí tienen sentido económico** en Polymarket, basadas en ineficiencias estructurales del mercado.  
No son estrategias de “trading genérico”, ni dependen de suerte, incentivos artificiales o rewards.

Las tres comparten infraestructura (event detection, market cache, execution), pero **no deben mezclarse en el mismo bot**.

---

## Visión General

| Estrategia | Tipo de Edge | Riesgo | Horizonte | Rol |
|----------|-------------|--------|-----------|-----|
| 1. Near-Resolution Liquidity | Informacional + Timing | Bajo | Minutos | Core |
| 2. Resolution Drift Arbitrage | Error estructural post-evento | Muy bajo | Minutos–Horas | Complementario |
| 3. Delayed Resolution Hedging | Gestión de riesgo / capital | Muy bajo | Horas–Días | Infraestructura |

---

# 1. Near-Resolution Liquidity Provider (Bot Principal)

## Qué es

Estrategia que **provee liquidez unilateral** cuando un evento **ya ha terminado en el mundo real**, pero **aún no ha sido resuelto por Polymarket**.

Permite a otros usuarios hacer **cashout inmediato** aceptando un pequeño descuento, mientras el bot captura ese diferencial con riesgo casi nulo.

---

## Ineficiencia explotada

- Polymarket resuelve con **latencia**
- Muchos usuarios quieren salir **antes de la resolución**
- El mercado queda sin liquidity providers profesionales
- El precio converge a 0.99 / 0.01, pero:
  - spreads son amplios
  - liquidez es limitada
  - hay pánico / urgencia

Esto crea una ventana temporal de oportunidad.

---

## Ejemplo concreto

Evento: *“Ganará el Equipo A el partido?”*

- El partido termina.
- El Equipo A gana claramente.
- Fuentes externas confirman resultado (API deportiva, múltiples feeds).

Estado en Polymarket:
- YES bid: 0.95
- YES ask: 0.99
- Liquidez baja.

### Acción del bot

- Coloca un **bid grande unilateral**:
  - BUY YES @ 0.98
- Usuarios aceptan vender a 0.98 para cobrar ya.
- Bot mantiene la posición hasta resolución.
- Resolución → payout = 1.00

### Resultado

- Beneficio ≈ 2% sobre el capital usado
- Tiempo de exposición: minutos–horas
- Riesgo: error en la confirmación del evento

---

## Características clave

- ✅ One-sided (no market making clásico)
- ✅ No depende de rewards
- ✅ Alta ROI por unidad de tiempo
- ✅ Escala con capital
- ❌ No funciona sin detección rápida del evento

---

## Cuándo NO entra el bot

- Resultado ambiguo
- Evento sin confirmación cruzada
- Polymarket ya ajustó precios correctamente
- Riesgo legal / suspensión del mercado

---

# 2. Resolution Drift Arbitrage (Bot Complementario)

## Qué es

Estrategia que **corrige errores de pricing** que aparecen **después de que el evento esté decidido**, pero **antes de la resolución oficial**.

Aquí el bot **no da liquidez**: **explota inconsistencias matemáticas o abandono del book**.

---

## Ineficiencia explotada

Tras el final del evento:

- Market makers se retiran
- Retail deja órdenes “zombis”
- El book puede quedar inconsistente:
  - YES + NO > 1
  - spreads absurdos
  - precios congelados lejos del outcome real

El mercado ya está muerto, pero aún no resuelto.

---

## Ejemplo concreto

Evento terminado, resultado claro.

Book en Polymarket:
- YES @ 0.97
- NO @ 0.06

(0.97 + 0.06 = 1.03 → error lógico)

### Acción del bot

- Compra el lado **incorrectamente caro o barato**
  - BUY NO @ 0.06 (si el outcome es NO)
  - o BUY YES @ 0.97 (si está mal anclado)
- Mantiene hasta resolución

### Resultado

- Arbitrage puro
- No necesita vender liquidez
- No depende del comportamiento de otros usuarios

---

## Características clave

- ✅ Muy bajo riesgo (evento ya decidido)
- ✅ Poco capital requerido
- ✅ Menos competencia
- ✅ Complementa al bot principal
- ❌ Menos frecuencia
- ❌ Depende de errores del book

---

## Diferencia con el Bot 1

| Near-Resolution | Resolution Drift |
|----------------|-----------------|
| Provee liquidez | Consume errores |
| Usuarios venden | Bot limpia book |
| Spread capturado | Error capturado |
| Más frecuente | Menos frecuente |

---

# 3. Delayed Resolution Hedging (Bot de Infraestructura)

## Qué es

Este bot **no busca beneficio directo**, sino **reducir riesgo y liberar capital** cuando Polymarket tarda en resolver eventos.

Su objetivo es **optimizar el capital total del desk**.

---

## Problema que resuelve

- Polymarket puede tardar **horas o días** en resolver
- Capital queda bloqueado
- Riesgo operativo (cancelaciones, disputas, errores)
- Exposición contable no cerrada

Mientras tanto:
- Otros mercados equivalentes ya reflejan el resultado

---

## Ejemplo concreto

Evento político resuelto en la realidad.

- Polymarket sigue sin resolver.
- Otro mercado equivalente:
  - está en 0.99
  - o ya resolvió
  - o es un proxy claro del resultado

### Acción del bot

- Compra el mercado correlacionado
- O abre posición opuesta equivalente
- Congela el resultado económico

Ejemplo:
- YES atrapado sin resolver
- Bot compra NO del mercado inverso equivalente

---

## Resultado

- PnL bloqueado ≈ asegurado
- Riesgo reducido a casi 0
- Capital mental y contable liberado
- Permite seguir operando otros eventos

---

## Características clave

- ✅ Reduce drawdowns
- ✅ Mejora capital efficiency
- ✅ No compite con nadie
- ✅ Muy bajo riesgo
- ❌ No genera PnL visible directo
- ❌ Solo útil con volumen grande

---

# Relación entre las tres estrategias

```

Event Detection Engine
↓
Market State Cache
↓
──────────────────────────────────
│  Strategy Layer               │
│                                │
│  1. Near-Resolution Liquidity  │
│  2. Resolution Drift Arb       │
│  3. Delayed Resolution Hedge   │
──────────────────────────────────
↓
Execution Engine

```

- Comparten **detección y datos**
- NO comparten decisiones
- NO se mezclan órdenes
- Cada una tiene su propio riesgo y lógica

---

# Conclusión Final

Estas tres estrategias cumplen algo clave:

- ✅ Edge estructural
- ✅ Automatizables
- ✅ Escalables
- ✅ No dependen de incentivos artificiales
- ✅ No dependen de suerte

No son “bots de trading”.
Son **sistemas de extracción de ineficiencia**.

Cualquier estrategia fuera de estas tres, en Polymarket hoy:
- o es marginal,
- o es puramente competitiva,
- o depende de rewards,
- o es ilegal.

Estas no.
```
