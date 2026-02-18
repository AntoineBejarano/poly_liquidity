# Plan de desarrollo: Estrategia Telegram Tipsters → PS3838

**Objetivo:** Permitir a cada usuario conectar su Telegram, seguir N grupos de tipsters, extraer tips (partido, selección, stake, odds), resolver el partido al evento/ID de PS3838, mostrar la info en la UI con clasificación de riesgo, y apostar en PS3838 de forma automática o con confirmación previa.

**Audiencia:** Ingeniería, producto.

**Última actualización:** 2026-02.

**Convenciones:**
- **Reutilizar:** componente o flujo ya existente en el código.
- **Nuevo:** componente o diseño a implementar.

**Adaptación a lo ya desarrollado:** Las cuentas (PS3838 y Telegram) se gestionan como el resto de credenciales del sistema (ExternalDataSource / venue connections). Esta estrategia se expone como **template** en el selector de estrategias. La lógica se implementa con el **sistema de grafos** existente (Decision, Support, Execution), definiendo grafos reutilizables (p. ej. `ps3838_engine`, `telegram_listener`) que se puedan intercambiar o componer con otras estrategias, e incluyendo **guardrails** en el Execution Graph al meter la apuesta.

---

## 1. Resumen ejecutivo

| Aspecto | Descripción |
|--------|-------------|
| **Tipo** | Estrategia basada en **template** (como Near-Resolution y Surebet Polymarket-Pinnacle). |
| **Fuente de señales** | Mensajes de grupos de Telegram (tipsters), vía sesión Telethon. |
| **Destino de ejecución** | PS3838 (API REST: Lines API + Bets API; autenticación HTTP Basic). |
| **Cuentas** | Usuario **selecciona** en la config de la estrategia: (1) cuenta PS3838 ya creada, (2) cuenta Telegram ya configurada. Ambas se crean/configuran **una vez** (igual que hoy las venue connections / ExternalDataSource). |
| **Dashboard** | Tras configurar la estrategia (cuentas + riesgo + modo), el usuario accede a un **dashboard personalizado** de esta estrategia: tips en lectura, tips leídos con toda la info, y si se metió o no la apuesta. |
| **Grafos** | Support/Execution reutilizables: `ps3838_engine`, listener Telegram, match resolution, place_bet con guardrails; intercambiables con otras estrategias. |
| **Reutilización** | Auth, Strategy + template config, ExternalDataSource (connector_type `ps3838` y `telegram`), grafos, Risk Engine, secrets. |

---

## 2. Objetivos y flujo de valor

### 2.1 Flujo de usuario

1. **Cuentas (una vez, como el resto del sistema):**
   - Usuario crea una **conexión PS3838** (igual que hoy las venue connections / ExternalDataSource): nombre, usuario y contraseña API; se guardan encriptados. La cuenta debe estar financiada.
   - Usuario crea una **conexión Telegram** (una vez): "Conectar cuenta de Telegram" → teléfono → código (y 2FA si aplica) → se guarda sesión encriptada → `get_dialogs()` → selección de grupos/canales con checkboxes → se guardan `monitored_chats`. Si la sesión falla más adelante, se pide reconexión (ver §5.3.1).
2. **Crear estrategia desde template:** Usuario elige el template **"Telegram Tipsters → PS3838"** en el selector de estrategias (junto a Near-Resolution, Surebet Polymarket-Pinnacle, etc.).
3. **Configuración de la estrategia (formulario del template):**
   - **Cuenta PS3838:** campo tipo SELECT con las conexiones PS3838 del usuario (ya ingresadas de antemano).
   - **Cuenta Telegram:** campo tipo SELECT con las conexiones Telegram del usuario (ya configuradas). Si no tiene ninguna, enlace a "Añadir cuenta Telegram" (flujo del paso 1).
   - Límites de riesgo: max_stake_per_tip, max_daily_stake, clasificación (opcional).
   - Modo: **apostar directamente** o **preguntar antes**.
4. **Dashboard personalizado:** Una vez guardada la estrategia (con las dos cuentas seleccionadas y el resto de opciones), el usuario entra al **dashboard de esta estrategia**, donde ve:
   - Tips que se **están leyendo** (en tiempo real).
   - Tips **ya leídos** con toda la info (partido, selección, stake, odds, match resuelto o no, risk_class).
   - Para cada tip: **si se metió o no la apuesta** en PS3838 (estado y ps3838_bet_id si aplica).
   - Acciones: aprobar/rechazar/ejecutar según el modo configurado.
5. Pipeline interno: mensajes Telegram → parse/Vision → match resolution (PS3838 Lines API) → TipIntent → Risk Engine → Execution Graph (con guardrails) → Place Bet en PS3838 si aplica.

### 2.2 Edge y valor

- Centralizar tips de varios grupos en una sola UI.
- Traducir texto libre (partido en Telegram) a apuesta concreta en PS3838 con verificación de odds y riesgo.
- Control de riesgo explícito y opción de confirmación humana antes de apostar.

---

## 3. Reutilización de la infraestructura existente

### 3.1 Backend

| Componente | Uso |
|------------|-----|
| **Auth** (`get_current_user`, JWT Stack) | Todas las APIs de la estrategia y config son por usuario. |
| **Strategy** (modelo, `created_by`) | Una estrategia por usuario creada desde el template `telegram_tipster_ps3838`. |
| **StrategyTemplateConfig + StrategyTemplate** | Añadir template igual que `surebet_polymarket_pinnacle`: `template_id`, `fields` (ps3838_source_id, telegram_source_id, risk, execution_mode), `compiler` → genera decision_graph + support_graphs + execution_graph. |
| **ExternalDataSource** | Cuentas como hoy: `connector_type: "ps3838"` (usuario/contraseña en connector_config o secrets) y `connector_type: "telegram"` (sesión encriptada + monitored_chats). `created_by` = usuario. En la config de la estrategia el usuario **selecciona** qué source_id usar (SELECT con options_source external_data_sources filtrado por tipo). |
| **Venue connections / listado** | Listar conexiones PS3838 (y Telegram) del usuario para el SELECT en el formulario del template. |
| **TipIntent** | Entidad para tips (ver §6); flujo PENDING → APPROVED/REJECTED → EXECUTED. |
| **Risk Engine** | Validar stake vs límites antes de aprobar; integrable con el existente. |
| **Grafos (Support / Execution)** | Grafos reutilizables: `ps3838_engine` (fixtures, odds, place_bet con guardrails), listener Telegram, match resolution; intercambiables con otras estrategias (ver §3.4). |
| **Secrets** | Mismo patrón que wallets/ExternalDataSource para credenciales (Fernet o el existente). |

### 3.2 Frontend

| Componente | Uso |
|------------|-----|
| **Estrategias: listado, detalle, live** | Template "Telegram Tipsters → PS3838" en el selector (como Surebet); formulario de config con SELECT de cuenta PS3838 y SELECT de cuenta Telegram (ya configuradas). |
| **Dashboard de la estrategia** | Vista personalizada para esta estrategia: tips en lectura, tips leídos (con toda la info), y si se metió o no la apuesta; acciones aprobar/rechazar/ejecutar. |
| **API client** (`lib/api.ts`), **WebSocket** | CRUD estrategias, listado TipIntents, streaming en tiempo real para el dashboard. |
| **Patrones de formularios** (Surebet) | Campos del template: ps3838_source_id, telegram_source_id (options_source external_data_sources), risk_config, execution_mode. |

### 3.4 Grafos reutilizables e intercambiables

La lógica se implementa con el **sistema de grafos ya existente** (Decision Graph, Support Graph, Execution Graph) para poder reutilizar y componer con otras estrategias:

- **PS3838 engine (Support + Execution):** Grafos que encapsulan: obtención de fixtures/odds (Lines API), match resolution (fuzzy match), y **colocación de apuesta (Place Bet)**. El nodo de "meter la apuesta" vive dentro de un **Execution Graph** para poder encadenar **guardrails** justo antes (p. ej. verificar límites, confirmar que las odds siguen vigentes, tope de stake, etc.). Otros templates podrían reutilizar el mismo `ps3838_engine` (p. ej. una estrategia que solo use odds de PS3838 para comparar).
- **Telegram listener:** Worker o Support Graph que mantiene el listener Telethon, parsea mensajes (texto + Vision para imágenes), escribe candidatos de tip en State Cache o encola TipIntents. La estrategia Tipster usa este grafo; en el futuro podría haber otras estrategias que consuman mensajes de Telegram de otra forma.
- **Match resolution:** Nodo o subgrafo que recibe tip parseado y devuelve eventId/lineId/odds de PS3838; reutilizable donde haga falta resolver "partido en texto" a evento PS3838.
- **Guardrails al meter la apuesta:** Dentro del Execution Graph que ejecuta Place Bet: nodos de validación (risk_check, odds_still_valid, max_stake, etc.) antes de llamar al nodo `place_bet_ps3838`. Así los guardrails son configurables e intercambiables como el resto de nodos.

Referencia: [Graph Nodes Reference](../architecture/graph-nodes-reference.md); mismo patrón que Surebet con `fetch_external_source` y nodos de ejecución.

### 3.5 Documentación y referencias

- **Near-Resolution plan:** L1/L2, frescura, risk, intents, UI trader (snapshot/deltas) como referencia de patrones.
- **Execution Engine:** ExecutionPlan, Execution Graph, plataformas (Polymarket vs otras).
- **Templates:** Añadir plantilla en `templates.md` y en backend `strategy_template_config` / `strategy_template`.

### 3.6 Flujo para crear una nueva plantilla

Para que una plantilla exista en la app (listado en **Crear Estrategia** y accesible por URL `?template=<id>`):

1. **Backend – Config del template**  
   En `backend/app/models/strategy_template_config.py`:
   - Definir una constante `StrategyTemplateConfig` con `template_id`, `name`, `description`, `category`, `fields` (campos del formulario) y `compiler` (nombre de la función que compila).
   - Añadir la entrada al diccionario `TEMPLATE_CONFIGS` con clave `template_id` (ej. `"telegram_tipster_ps3838"`).

2. **Backend – Compiler**  
   En `backend/app/core/strategy_engine/template_compiler.py`:
   - Implementar la función de compilación (ej. `compile_telegram_tipster_ps3838(config)`) que devuelva `decision_graph`, `execution_graph`, `support_graphs` y opcionalmente `risk_config`.
   - Registrar la función en el diccionario de compilers que usa `compile_strategy(template_id, config)`.

3. **Reiniciar el backend**  
   Las plantillas se leen al arrancar. Si el servidor estaba levantado antes de añadir la plantilla, hay que reiniciarlo para que `GET /strategy-templates` y `GET /strategy-templates/{template_id}` devuelvan la nueva plantilla.

4. **Frontend (opcional)**  
   Si quieres una tarjeta directa en **Nueva Estrategia** (`/strategies/new`), añadir una entrada en el array `STRATEGY_TEMPLATES` de `frontend/app/strategies/new/page.tsx` con `href: '/strategies/create?template=<template_id>'`.

Si aparece *"Template 'xxx' not found"* al usar `?template=xxx`, suele deberse a que el backend en ejecución es una instancia antigua: **reiniciar el backend** tras asegurarse de que la plantilla está en `TEMPLATE_CONFIGS` y el compiler registrado.

---

## 4. API de PS3838 (referencia externa)

PS3838 expone una **API REST pública** para consultar líneas y colocar apuestas. No hace falta cookies ni automatización de navegador.

- **Documentación:** [PS3838 API](https://ps3838api.github.io/) · [Getting Started](https://ps3838api.github.io/GettingStarted.html) · [Lines API](https://ps3838api.github.io/docs?api=lines) · [OpenAPI (betsapi.yaml)](https://raw.githubusercontent.com/ps3838api/api-spec/master/OpenAPI/betsapi.yaml).
- **Autenticación:** HTTP Basic (usuario y contraseña en Base64 en el header `Authorization`). La cuenta debe estar **financiada** para acceder a la API.
- **Formato:** JSON solo; fechas/horas en GMT, ISO 8601. `Accept: application/json`. Compresión HTTP soportada.
- **Antiduplicación:** `uniqueRequestId` en las peticiones de apuesta; el servidor lo guarda ~30 min para evitar duplicados.

### 4.1 Líneas (Lines API)

- **Deportes y ligas:** Get Sports, Get Leagues.
- **Eventos:** **Get Fixtures** — `/v3/fixtures` devuelve la lista de eventos ofrecidos. Actualizaciones vía peticiones delta (parámetro `since`).
- **Odds:** **Get Odds** — `/v4/odds` devuelve las cuotas ofrecidas. También delta con `since`.
- **Línea concreta (opcional):** **Get Line** — límites de stake exactos para una línea; los límites en Get Odds son orientativos.
- **Tipos de apuesta:** SPREAD, MONEYLINE, TOTAL_POINTS, TEAM_TOTAL_POINTS; parlays, teasers, specials (v4 para odds/parlay).

**Límites de uso (Fair Use):**
- Snapshot (sin `since`): máximo **1 vez cada 60 segundos** por deporte.
- Delta (con `since`): máximo **1 vez cada 5 segundos** por deporte.

### 4.2 Apuestas (Bets API)

- **Straight bet:** Get Fixtures → Get Odds (y opcionalmente Get Line) → **Place Bet** con los IDs obtenidos (sportId, leagueId, eventId, periodNumber, lineId, team/handicap/points según tipo).
- **Parlay:** Get Fixtures → Get Odds → **Get Parlay Lines** (POST `/line/parlay`) con legs; si status = VALID → **Place Parlay Bet** con los lineIds devueltos.
- **Estado:** **Get Bets** para comprobar el estado de la apuesta (por bet id). Para live en PENDING_ACCEPTANCE, consultar cada ~5 s.

### 4.3 Uso en este plan

- **Match resolution:** llamar a Get Fixtures (`/v3/fixtures`) y Get Odds (`/v4/odds`) filtrando por deporte/liga; emparejar equipos del tip con los eventos; obtener eventId, periodNumber, lineId (y altLineId si aplica).
- **Ejecución:** Place Bet (Bets API) con los parámetros mapeados desde la respuesta de Get Odds (sportId, leagueId, eventId, periodNumber, team, lineId/altLineId, handicap/points según tipo). Respetar `uniqueRequestId` y rate limits.

**Nota:** La disponibilidad de deportes/ligas puede variar por políticas internas del proveedor (p. ej. en algunos entornos se han reducido a Baseball, Basketball, NFL, MMA, Soccer, Tennis). Verificar con **Get Sports / Get Leagues** al inicio y cachear la lista disponible; no asumir un catálogo fijo.

---

## 5. Telegram: obtención de mensajes

- **Bot API:** el bot se añade a los grupos; solo recibe mensajes **nuevos** desde que está en el grupo (no historial completo). Requiere que el usuario cree un bot y lo añada manualmente a cada grupo.
- **Telethon (MTProto):** sesión de usuario; permite listar todos los grupos/canales del usuario y leer mensajes en tiempo real sin que el usuario tenga que crear bots ni añadir nada. **Recomendado para el SaaS** (ver §5.3).

---

### 5.3 Integración plug-and-play con sesión de usuario (Telethon) + OpenAI Vision para lectura de imágenes

Para lograr una experiencia **plug-and-play** real en el SaaS (sin que el usuario tenga que crear bots ni añadir manualmente nada a los grupos), se utilizará una **sesión de usuario** mediante la librería **Telethon** (cliente MTProto oficial de Telegram). Este enfoque permite:

- Conectar la cuenta de Telegram del usuario de forma similar a un "Login with Google".
- Listar automáticamente **todos** los grupos y canales donde el usuario ya está miembro.
- Permitir al usuario seleccionar con checkboxes los chats a monitorear.
- Leer mensajes nuevos en tiempo real solo de los chats seleccionados.

**Flujo de conexión para el usuario (frontend + backend):**

1. En el dashboard aparece el botón **"Conectar cuenta de Telegram"**.
2. Modal paso 1: introduce **número de teléfono** (+XX XXX XXX XXX).
3. Backend envía código de verificación a la app Telegram del usuario (`client.send_code_request(phone)`).
4. Modal paso 2: usuario pega el código de 5 dígitos (y contraseña 2FA si la tiene).
5. Backend completa el login (`client.sign_in()`) y guarda la **sesión como string encriptado** (Fernet o similar, en la BD del usuario).
6. Inmediatamente después, se llama a `client.get_dialogs()` para obtener la lista completa de grupos/canales.
7. Frontend muestra una lista con checkboxes: título del grupo/canal, tipo (grupo/canal), username si existe.
8. Usuario selecciona los deseados → se guardan los `chat_id` (IDs numéricos negativos) en `user.telegram_monitored_chats`.

**Recepción y procesamiento de mensajes (listener Telethon):**

- Se inicia un listener persistente por usuario (o un worker global que gestione múltiples sesiones).
- Handler: `@client.on(events.NewMessage(chats=user.telegram_monitored_chats))`
- Para cada mensaje nuevo se evalúan tres casos:

  1. **Solo texto** (`message.raw_text` o `message.message`): se parsea directamente con regex/heurísticas existentes.
  2. **Mensaje con foto(s) + caption útil**: se prioriza el caption (`message.message`) si contiene indicadores de tip (ej. "Over 2.5", "@1.85", "stake 3", etc.).
  3. **Mensaje con foto(s) sin caption útil o caption incompleto**: se descarga la imagen (`await message.download_media(file=bytes)`) y se envía a **OpenAI Vision** (modelo `gpt-4o` o `gpt-4o-mini`) para extracción inteligente.

**Uso de OpenAI API (Vision / multimodal):**

Se usará la API de OpenAI para procesar las imágenes de tips (capturas de pantalla de tickets de apuestas). OpenAI Vision es superior a OCR tradicional (Tesseract/EasyOCR) porque entiende contexto, layouts complejos, texto pequeño/borroso y razona sobre el contenido.

**Prompt recomendado para OpenAI (optimizado para tips de apuestas):**

> Eres un experto en apuestas deportivas y extracción de tips. Analiza esta imagen (captura de ticket o tipster) y el caption proporcionado (si existe). Extrae la información clave en formato JSON estricto:
>
> ```json
> {
>   "partido": "Equipo Local vs Equipo Visitante" o null,
>   "fecha_hora": "2026-02-20 20:00" o null (formato ISO si posible),
>   "seleccion": "Over 2.5" | "1" | "X" | "2" | "AH -1.5 Local" | "BTTS Yes" | etc.,
>   "cuota": 1.92 | null,
>   "stake": 4.5 | null (unidades o valor absoluto),
>   "tipo_apuesta": "TOTAL_POINTS" | "MONEYLINE" | "SPREAD" | "BTTS" | "THREE_WAY" | etc.,
>   "confianza": 0.0-1.0 (tu estimación de que es un tip válido y bien extraído),
>   "error": null | "no_es_tip" | "imagen_no_legible"
> }
> ```
>
> Reglas:
> - Usa el caption como contexto prioritario si está presente.
> - Si no hay tip claro o la imagen no contiene apuesta, responde solo con `{"error": "no_tip"}`.
> - Responde ÚNICAMENTE con JSON válido, sin texto adicional.

**Integración en el pipeline:**

- Descargar bytes de la foto → convertir a base64 → enviar en `messages` con `type: "image_url"` y `url: "data:image/jpeg;base64,..."`.
- Combinar caption + imagen en el mismo prompt para mayor precisión.
- El JSON devuelto se usa directamente para alimentar el **match resolution** contra PS3838 (buscar evento por equipos + fecha + tipo de apuesta).
- Si hay múltiples fotos (álbum), procesar la principal o la que tenga caption.

**Ventajas clave para el SaaS:**

- Experiencia 100% plug-and-play: usuario solo pone teléfono y código → ya puede seleccionar grupos.
- Lee grupos privados/supergroups donde el usuario ya está.
- Maneja la realidad de los tipsters (muchos envían tips en imágenes).
- OpenAI Vision ofrece extracción mucho más robusta y contextual que OCR local.

**Consideraciones:**

- Sesiones Telethon son "userbot" → riesgo bajo de ban si solo se lee (no se envían mensajes ni se une masivamente).
- Coste OpenAI: ~0.3–1 centavo por imagen procesada con `gpt-4o-mini` (modelo eficiente para este uso en 2026).
- Guardar solo lo parseado (nunca imágenes ni mensajes completos más allá de lo necesario para auditoría).

Una vez extraída la info (de texto o imagen vía OpenAI), se procede al **match resolution** normal: buscar fixtures en PS3838 Lines API por deporte/liga/equipos/fecha, fuzzy match de nombres, obtener eventId/lineId/odds actuales, y generar TipIntent.

#### 5.3.1 Manejo de sesión Telegram: solo una vez por defecto, reconexión inteligente

La cuenta Telegram se configura **una sola vez**; el uso normal es conectar con la sesión guardada. Si algo falla, se marca y se pide reconexión.

- **Primera conexión:** Siempre se pide teléfono + código (y 2FA si tiene). Se guarda la StringSession encriptada (y opcionalmente `monitored_chats` tras `get_dialogs()`).
- **Uso normal:** Al arrancar el listener (o al activar la estrategia), se intenta `await client.connect()` y se comprueba `if not await client.is_user_authorized()`. Si no está autorizado, se marca la conexión como **"sesión inválida"** y en la UI se pide **reconexión** (volver a introducir código o teléfono+código).
- **Cuándo forzar reconexión (pedir código nuevo):**
  - Cada vez que el usuario **activa la estrategia** y la sesión falla (AuthKeyNotFound, sesión no autorizada, etc.).
  - **Opcional:** cada 3–6 meses como recordatorio de seguridad (revisión de sesiones activas en Telegram), igual que en muchos SaaS.
  - Si se detectan **errores repetidos en el listener** (p. ej. `UpdatesTooLong`, desconexión constante), forzar relogin y marcar sesión inválida.
- **Manejo explícito en el worker:** En `connect()` y en el bucle del listener (p. ej. `run_until_disconnected()`), usar try-except para **FloodWaitError** (retry con backoff; si el wait supera un umbral razonable, marcar sesión inválida y notificar a la UI para reconexión) y **AuthKeyUnregistered** / **AuthKeyError** (marcar sesión inválida de inmediato y notificar UI para reconexión). Así el usuario recibe feedback claro y puede reconectar sin depender de logs.
- En el formulario de la estrategia, si el usuario selecciona una cuenta Telegram marcada como "sesión inválida", mostrar aviso y botón "Reconectar cuenta Telegram" que abre el flujo de código de nuevo.

---

## 6. Modelo de datos y flujo de intents

### 6.1 Opción A: Reutilizar ExecutionIntent

- `event_id`: podría ser un "evento virtual" creado por tip (p. ej. evento sintético por tip_id) o nullable para esta estrategia.
- `context`: `{ "source": "telegram_tip", "telegram_message_id": "...", "parsed": {...}, "ps3838_event_id": ..., "ps3838_line_id": ..., "risk_class": "medium", "raw_message": "..." }`.
- `reason`: descripción legible del tip (ej. "Tip: Real Madrid vs Barça - 1").
- Limitación: ExecutionIntent está muy acoplado a `event_id` (FK a `events.id`). Si no queremos crear eventos sintéticos, puede ser incómodo.

### 6.2 Opción B (recomendada): TipIntent o TelegramTipIntent

Nueva tabla por usuario/estrategia:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID | PK |
| strategy_id | UUID FK | Estrategia "Telegram Tipster → PS3838" |
| user_id | string FK | Creador/dueño (created_by) |
| telegram_message_id | string | ID del mensaje en Telegram (dedup) |
| telegram_chat_id | string | Grupo/canal de origen |
| raw_text | text | Mensaje original |
| parsed | JSONB | Equipos, selección (1X2, over/under, etc.), stake, odds si viene |
| ps3838_event_id | bigint nullable | ID evento PS3838 (resuelto) |
| ps3838_league_id | int nullable | Liga en PS3838 |
| ps3838_period_number | int nullable | Periodo (0=full, etc.) |
| ps3838_line_id / bet_type | según API | Línea o tipo de apuesta en PS3838 |
| ps3838_odds | decimal nullable | Cuota actual PS3838 (en el momento de resolución) |
| suggested_stake_usd | decimal | Stake a apostar (calculado según reglas del usuario) |
| risk_class | string | "low" \| "medium" \| "high" (clasificación interna) |
| status | string | PENDING \| APPROVED \| REJECTED \| EXECUTED \| FAILED |
| ps3838_bet_id | string nullable | ID de la apuesta en PS3838 una vez ejecutada |
| approved_at, rejected_at, executed_at | datetime | |
| rejection_reason | string | |
| created_at | datetime | |

Ventaja: no contamina el modelo de ExecutionIntent (orientado a Polymarket/eventos); el flujo de aprobación/ejecución es análogo y se puede reutilizar Risk Engine y un "TipExecutionRunner" que llame a la Bets API de PS3838.

### 6.3 Configuración: cuentas como ExternalDataSource y estrategia como template

Las cuentas se gestionan **como el resto del sistema** (igual que las venue connections / ExternalDataSource de Surebet):

- **PS3838:** El usuario crea de antemano una o más **ExternalDataSource** con `connector_type: "ps3838"`. En `connector_config` (o vía secrets) se guardan usuario y contraseña API encriptados. La cuenta debe estar financiada. En el **formulario del template** de la estrategia, un campo tipo **SELECT** (`ps3838_source_id`) lista las fuentes del usuario con `connector_type=ps3838` (options_source external_data_sources filtrado por tipo).
- **Telegram:** El usuario configura **una vez** una o más conexiones Telegram (ExternalDataSource `connector_type: "telegram"` o tabla equivalente): sesión Telethon encriptada + `monitored_chats` tras el flujo teléfono → código → get_dialogs() → checkboxes. En el formulario del template, un campo **SELECT** (`telegram_source_id`) lista las conexiones Telegram del usuario. Si la sesión pasa a inválida, se pide reconexión (§5.3.1).
- **Estrategia (instancia del template):** Al crear/editar la estrategia desde el template "Telegram Tipsters → PS3838", el usuario solo **selecciona** la cuenta PS3838 y la cuenta Telegram (ya configuradas), más los campos del template: `risk_config` (max_stake_per_tip, max_daily_stake), `execution_mode` ("auto" | "confirm_before"), filtros opcionales (deportes, ligas, mínima cuota). El compiler del template genera el decision_graph, support_graphs y execution_graph con los `source_id` elegidos (igual que Surebet con `{{pinnacle_source_id}}`).

Persistencia: **ExternalDataSource** con `connector_type` "ps3838" y "telegram", `created_by` = user; credenciales en connector_config encriptado o en el mismo sistema de secrets que wallets. La estrategia guarda en su config (o en StrategyExternalDataSource si se añade) los IDs de las fuentes seleccionadas.

### 6.4 Definición del template (backend)

Registrar el template igual que Surebet y Near-Resolution:

- **`strategy_template_config.py`:** Añadir `TELEGRAM_TIPSTER_PS3838_CONFIG` con `template_id="telegram_tipster_ps3838"`, `name`, `description`, `category` (p. ej. "tipsters"), `compiler="compile_telegram_tipster_ps3838"`, y `fields`:
  - `ps3838_source_id`: tipo SELECT, required, section "Cuentas", `options_source`: "external_data_sources" (filtrar por connector_type ps3838), label "Cuenta PS3838".
  - `telegram_source_id`: tipo SELECT, required, section "Cuentas", options_source para conexiones Telegram, label "Cuenta Telegram".
  - Campos de **clasificación de riesgo y bankroll** (ver §8): `risk_rules`, `max_stake_per_tip`, `max_daily_stake`, `max_daily_bets`, `min_odds`, `max_odds`; y sección "Bankroll & Stake": `staking_mode`, `percent_of_balance`, `flat_stake`, `fixed_units`, `kelly_fraction`, `min_stake`, `reserve_percentage`.
  - `execution_mode`: SELECT, opciones "auto" / "confirm_before", section "Ejecución".
- **`strategy_template.py`:** Añadir entrada `telegram_tipster_ps3838` con `decision_graph`, `support_graphs` (p. ej. telegram_listener, fetch_ps3838_fixtures/odds, match_resolution), `execution_graph` (guardrails + place_bet_ps3838), `risk_config` por defecto. Usar placeholders `{{ps3838_source_id}}`, `{{telegram_source_id}}` en los nodos que necesiten el source_id.
- **`template_compiler.py`:** Implementar `compile_telegram_tipster_ps3838(config)` que tome los valores del formulario y monte el JSON del decision_graph, support_graphs y execution_graph (igual que `compile_surebet_polymarket_pinnacle`).

---

## 7. Match resolution: Telegram partido → PS3838 event ID

**Problema:** El mensaje dice "Real Madrid - Barcelona, 1" o "Madrid vs Barça Over 2.5"; hay que identificar el evento correcto en PS3838 y la línea (mercado) concreta.

### 7.1 Pipeline

1. **Parsear mensaje** (regex + heurísticas o pequeño NLP): extraer equipos (o nombres normalizados), tipo de apuesta (1X2, over/under, BTTS, etc.), stake, odds si se mencionan.
2. **Obtener candidatos de PS3838:** llamar a **Get Fixtures** (`/v3/fixtures`) y **Get Odds** (`/v4/odds`) de la Lines API, filtrando por sportId (y opcionalmente leagueId). Respetar rate limits (snapshot 1/60 s por deporte, delta 1/5 s). Rango de fechas: hoy + 1–2 días.
3. **Fuzzy match de equipos:** normalizar nombres (quitar acentos, "Real Madrid" vs "Madrid", abreviaturas). Comparar con los nombres de equipos en la respuesta de Fixtures (Event Type → home/away). Métrica: Levenshtein o similar; umbral de confianza.
4. **Selección de mercado:** según tipo de apuesta (1, X, 2, Over 2.5, etc.) mapear a `periodNumber` y `lineId` (y `altLineId` si aplica para Spread/Total Points). Usar la guía de mapeo Get Odds → Place Bet de la doc (team, handicap, points).
5. **Output:** `ps3838_event_id`, `ps3838_league_id`, `period_number`, `line_id`, odds actuales. **Confidence score** (ej. 0–1) para mostrarlo en UI y, si está por debajo de umbral, forzar modo "preguntar" o marcar como "revisar manualmente".
6. **Guardrail humano con OpenAI:** Si el tip viene de OpenAI Vision y devuelve **confianza < 0.7** o **error** (p. ej. `"error": "no_es_tip"` o `"imagen_no_legible"`), forzar en UI **"revisar manualmente"** o tratar como modo "preguntar" (no auto-ejecutar). Refuerza el guardrail humano cuando la extracción es dudosa.

### 7.2 Mejoras iterativas

- Cache de fixtures por league/day respetando Fair Use (snapshot 60 s, delta 5 s por deporte).
- Permitir al usuario elegir manualmente entre varios candidatos si el sistema devuelve varios matches.
- Aprendizaje de alias (ej. "Barça" → "Barcelona") por usuario o global.

---

## 8. Clasificación de riesgo y Bankroll Management

La estrategia incorpora un **Risk Engine** avanzado y completamente configurable por el usuario que combina dos capas de protección:

1. **Clasificación de riesgo del tip** (low / medium / high / reject)
2. **Bankroll Management dinámico** (cálculo inteligente del stake según el balance real de la cuenta PS3838)

Ambas capas se ejecutan como **guardrails** dentro del Execution Graph antes de cualquier llamada a `place_bet_ps3838`. Esto garantiza que nunca se ejecute una apuesta que el usuario no haya aprobado explícitamente según sus propias reglas.

### 8.1 Clasificación de riesgo del tip

El Risk Engine evalúa cada TipIntent (ya parseado y resuelto contra PS3838) y asigna una clase de riesgo según las reglas definidas por el usuario.

**Parámetros configurables en la UI (dentro del formulario del template):**

| Parámetro | Tipo | Valor por defecto | Descripción |
|-----------|------|-------------------|-------------|
| `risk_rules` | JSON / Formulario avanzado | - | Reglas personalizadas (ver ejemplos abajo) |
| `max_stake_per_tip` | Number | 50 € | Stake máximo absoluto por apuesta |
| `max_daily_stake` | Number | 300 € | Stake máximo total en 24h |
| `max_daily_bets` | Number | 15 | Número máximo de apuestas por día |
| `min_odds` | Decimal | 1.60 | Cuota mínima aceptable |
| `max_odds` | Decimal | 3.50 | Cuota máxima aceptable |

**Ejemplos de reglas de clasificación (configurable en UI con editor visual o JSON):**

```json
{
  "low": "suggested_stake <= 30 && odds >= 1.70 && odds <= 2.40 && daily_stake_today + suggested_stake <= max_daily_stake",
  "medium": "suggested_stake <= 60 && odds >= 1.50 && daily_bets_today < max_daily_bets",
  "high": "suggested_stake > 60 || odds > 4.00 || daily_stake_today > max_daily_stake * 0.7",
  "reject": "suggested_stake > max_stake_per_tip || daily_stake_today + suggested_stake > max_daily_stake || odds < min_odds"
}
```

- **En modo "apostar directamente"** → solo se ejecutan tips clasificados como **low** o **medium** (configurable).
- **En modo "preguntar antes"** → se muestran todos los tips con su clasificación y el usuario decide.

### 8.2 Bankroll Management (Stake Calculation) – Totalmente configurable por el usuario

Dado que los usuarios son apostadores profesionales, el sistema **nunca asume un stake fijo**. El stake final se calcula dinámicamente justo antes de apostar, usando el **balance real** de la cuenta PS3838.

**Parámetros configurables en la UI (sección "Bankroll & Stake" del template):**

| Campo | Tipo | Opciones / Rango | Descripción / Uso recomendado |
|-------|------|------------------|-------------------------------|
| `staking_mode` | SELECT | percent_balance (default), flat, fixed_units, kelly, half_kelly | Modo de cálculo del stake |
| `percent_of_balance` | Number | 0.1 – 5.0% del balance disponible | Recomendado 0.5–2% |
| `flat_stake` | Number | ≥ 5 | Stake fijo en moneda de la cuenta (ej. 50 €) |
| `fixed_units` | Number | 1 – 10 | Unidades fijas (1 unidad = valor configurado por usuario) |
| `kelly_fraction` | Number | 0.1 – 1.0 | Fracción de Kelly (0.25–0.5 recomendado para pros) |
| `min_stake` | Number | ≥ 5 | Stake mínimo absoluto |
| `max_stake_per_tip` | Number | (ya existe) | Tope absoluto por tip |
| `reserve_percentage` | Number | 0 – 30% | % del balance que siempre se reserva (no se toca) |

**Cómo se calcula el stake (flujo real en el Execution Graph):**

1. Se llama a **GET /v1/client/balance** (o endpoint equivalente de PS3838) → se obtiene `availableBalance`.
2. Se calcula el **stake bruto** según `staking_mode`:
   - **percent_balance:** `stake = availableBalance × (percent_of_balance / 100)`
   - **flat:** `stake = flat_stake`
   - **fixed_units:** `stake = fixed_units × unit_value` (unit_value configurable globalmente por usuario)
   - **kelly / half_kelly:** se calcula `edge = (odds × probabilidad_estimada - 1)`. La probabilidad puede venir del tipster, del modelo interno o configurada manualmente.
3. Se aplica el **ajuste final:**

```text
stake_final = min(
    max(stake_bruto, min_stake),
    max_stake_per_tip,
    availableBalance × (1 - reserve_percentage/100)
)
```

4. **Guardrail final:** si `stake_final > availableBalance` → se rechaza automáticamente (FAILED: insufficient_balance) y se notifica al usuario en el dashboard.

### 8.3 Integración en el Execution Graph (guardrails)

Todos los cálculos anteriores se ejecutan como guardrails secuenciales dentro del `ps3838_engine`:

```text
TipIntent APPROVED
    ↓
[Guardrail] get_ps3838_balance()
    ↓
[Guardrail] calculate_stake() + apply_risk_rules()
    ↓
[Guardrail] check_balance_sufficient() + event_confirmation()
    ↓
[Guardrail] odds_still_valid()
    ↓
place_bet_ps3838(stake_final)
```

Si **cualquier** guardrail falla → el estado pasa a REJECTED o FAILED con `rejection_reason` claro y se muestra en el dashboard.

### 8.4 Ventajas para apostadores profesionales

- **Control total:** cada usuario define exactamente cómo quiere gestionar su bankroll.
- **Protección automática** contra over-betting.
- **Transparencia total:** en el dashboard se muestra siempre:
  - Balance actual de PS3838
  - Stake calculado y motivo del cálculo
  - % del bankroll que representa
  - Clasificación de riesgo del tip
- **Fácil de ajustar** en cualquier momento sin editar la estrategia (parámetros en el formulario del template).

---

## 9. Ejecución en PS3838 (dentro del Execution Graph, con guardrails)

- La colocación de la apuesta se implementa como **nodo(s) del Execution Graph** reutilizable (`ps3838_engine`), de modo que otras estrategias puedan usar el mismo grafo y se puedan **encadenar guardrails** justo antes de Place Bet.
- **Guardrails en el Execution Graph:** Antes del nodo que llama a Place Bet (p. ej. `place_bet_ps3838`), se encadenan nodos de validación: verificación de límites (risk_check), confirmación de que las odds siguen vigentes (odds_still_valid), tope de stake (max_stake), etc. Así los guardrails son configurables e intercambiables como el resto de nodos; el Place Bet solo se ejecuta si pasan todos.
- **Bets API:** El nodo `place_bet_ps3838` (o equivalente) llama a Place Bet (Bets API) con HTTP Basic usando las credenciales de la ExternalDataSource seleccionada. Parámetros: sportId, leagueId, eventId, periodNumber, team/handicap/points según tipo, lineId/altLineId, stake; `uniqueRequestId` para evitar duplicados.
- **Get Bets:** para comprobar estado de la apuesta (PENDING_ACCEPTANCE → aceptada/rechazada); en live consultar cada ~5 s si hace falta.
- Manejo de errores: línea cerrada, odds cambiadas, límites de cuenta, credenciales inválidas; reflejar en estado (FAILED, rejection_reason) y en el dashboard.
- Trazabilidad: guardar `ps3838_bet_id`, timestamp, request/response sanitizado en logs o en `context` del intent.

---

## 10. UI

### 10.1 Cuentas (una vez, fuera del template)

- **PS3838:** Pantalla o sección "Conexiones" / "Fuentes de datos": crear conexión tipo PS3838 (nombre, usuario, contraseña); se guarda encriptado. Igual que hoy las venue connections (Pinnacle/Bet365).
- **Telegram:** Botón "Conectar cuenta de Telegram" (en la misma sección o en configuración de cuenta): modal teléfono → código (y 2FA si aplica) → guardar sesión → `get_dialogs()` → listado con checkboxes de grupos/canales → guardar `monitored_chats`. Si la sesión está inválida (§5.3.1), mostrar "Reconectar cuenta Telegram".

### 10.2 Configuración de la estrategia (formulario del template)

- El usuario elige el template **"Telegram Tipsters → PS3838"** en el selector de estrategias (como Near-Resolution o Surebet).
- Formulario generado por el template (igual que Surebet con `pinnacle_source_id`):
  - **Cuenta PS3838:** SELECT con las conexiones PS3838 del usuario (ya creadas de antemano). Obligatorio.
  - **Cuenta Telegram:** SELECT con las conexiones Telegram del usuario (ya configuradas). Si no tiene ninguna, enlace a "Añadir cuenta Telegram" (flujo §10.1).
  - Nombre, descripción (opcional).
  - **Riesgo:** max_stake_per_tip, max_daily_stake; reglas de clasificación (opcional en MVP).
  - **Ejecución:** toggle "Apuesta automática" vs "Preguntar antes de apostar".
- Al guardar, se crea/actualiza la estrategia con los `source_id` seleccionados y se compila el grafo (compiler del template).

### 10.3 Dashboard personalizado de la estrategia

Una vez las dos cuentas están seleccionadas y la estrategia guardada, el usuario accede al **dashboard de esta estrategia** (vista específica para "Telegram Tipsters → PS3838"):

- **Tips que se están leyendo:** flujo en tiempo real (mensajes entrantes, parse en curso, match resolution en curso).
- **Tips ya leídos (con toda la info):** lista/panel con: mensaje original, parseado (partido, selección, stake, odds), partido resuelto en PS3838 (nombre + evento ID) o "Sin match / Revisar", odds PS3838 actuales, stake sugerido, risk_class, estado (Pendiente / Aprobado / Rechazado / Ejecutado / Fallido).
- **Indicador Odds PS3838 vs tip:** Para cada tip, mostrar si las odds actuales de PS3838 son **mejores o peores** que las del tip (cuota del tipster): p. ej. **verde** si la cuota PS3838 es mayor que la del tip (mejor para el apostante) o se ha mejorado; **rojo** si es menor (peor). Da valor rápido al trader para decidir si sigue teniendo sentido apostar.
- **Si se metió o no la apuesta:** para cada tip, indicador claro de si la apuesta se colocó en PS3838 (y ps3838_bet_id si aplica) o no (rechazada, fallida, pendiente de confirmación).
- **Acciones:** [Aprobar] [Rechazar] [Ejecutar en PS3838] según el modo configurado; filtros por grupo, estado, riesgo; selección manual de match cuando hay varios candidatos.
- WebSocket o polling para actualizaciones en tiempo real.

### 10.4 Histórico

- Historial de tips (con estado final y si se metió o no la apuesta en PS3838), para análisis y ajuste de límites; puede ser una pestaña o sección del mismo dashboard.

---

## 11. Fases de implementación sugeridas

### Fase 1 – Cuentas y grafos base (alineado con lo existente)

1. **ExternalDataSource:** Extender con `connector_type: "ps3838"` y `"telegram"`. PS3838: connector_config (o secrets) con usuario/contraseña encriptados. Telegram: connector_config con sesión encriptada + `monitored_chats` (lista de chat_id). CRUD por usuario; listado filtrado por tipo para los SELECT del template.
2. **Cliente PS3838 API y nodos:** Cliente HTTP para Lines API y Bets API; nodos reutilizables: `fetch_ps3838_fixtures`, `fetch_ps3838_odds`, `place_bet_ps3838` (usando credenciales de la ExternalDataSource indicada por source_id). Respetar rate limits y `uniqueRequestId`.
3. **Match resolution:** Nodo o subgrafo que recibe tip parseado y devuelve eventId/lineId/odds; fuzzy match contra fixtures/odds de PS3838.
4. **Template y compiler:** Registrar template `telegram_tipster_ps3838` en `strategy_template_config.py` y `strategy_template.py` con fields ps3838_source_id, telegram_source_id, risk, execution_mode; implementar `compile_telegram_tipster_ps3838` en `template_compiler.py` (grafos con `{{ps3838_source_id}}`, `{{telegram_source_id}}`).

### Fase 2 – Telegram: conexión una vez y listener (grafos)

5. **Flujo de conexión Telegram:** Login Telethon (send_code_request, sign_in, get_dialogs), guardar sesión encriptada y monitored_chats en ExternalDataSource (o tabla vinculada). Manejo de sesión inválida: marcar y pedir reconexión (§5.3.1).
6. **Parser y Vision:** Regex/heurísticas para texto; OpenAI Vision para imágenes (prompt JSON tip). Implementar función **`openai_extract_tip(image_bytes, caption)`** que llame a `chat.completions` (modelo gpt-4o o gpt-4o-mini) con el prompt de extracción de tip, la imagen como `image_url` (base64), y **`response_format: { type: "json_object" }`** para forzar salida JSON estructurada y evitar texto libre. Integrar en el grafo o worker que alimenta tips.
7. **Listener Telethon como Support Graph o worker:** `NewMessage(chats=monitored_chats)`; para cada mensaje: texto → parse; imagen sin caption útil → Vision → JSON. Dedup por message_id. Escribir candidatos a State Cache o crear TipIntent (PENDING).
8. **Execution Graph con guardrails:** Grafo que recibe TipIntent aprobado y ejecuta: nodos risk_check, odds_still_valid, max_stake (guardrails) → nodo place_bet_ps3838. Reutilizable como `ps3838_engine`.

### Fase 3 – Pipeline completo y APIs

9. **Pipeline tip completo:** Mensaje → parse/Vision → match resolution (PS3838 Lines) → TipIntent (PENDING). Publicar a L2/WebSocket para el dashboard.
10. **APIs REST:** Listar/actualizar TipIntents; aprobar/rechazar/ejecutar (encola ejecución vía Execution Graph). Risk Engine integrado con TipIntent; modo auto según execution_mode.
11. **Dashboard backend:** Endpoints para el dashboard de la estrategia: tips en lectura, tips leídos con toda la info, estado de apuesta (metida o no, ps3838_bet_id).

### Fase 4 – Frontend: cuentas, template y dashboard

12. **Cuentas (una vez):** UI para crear conexión PS3838 (como venue connection) y "Conectar cuenta Telegram" (teléfono → código → get_dialogs → checkboxes → guardar). Reconexión cuando sesión inválida.
13. **Configuración de estrategia:** Template "Telegram Tipsters → PS3838" en el selector; formulario con SELECT cuenta PS3838, SELECT cuenta Telegram, riesgo, execution_mode. Guardar estrategia con source_ids y grafos compilados.
14. **Dashboard personalizado:** Vista de la estrategia: tips que se están leyendo, tips leídos (info completa), si se metió o no la apuesta; acciones Aprobar/Rechazar/Ejecutar; filtros; selección manual de match cuando haya varios candidatos. WebSocket o polling.
15. **Histórico:** Pestaña o sección con historial de tips y resultado de apuesta.

### Fase 5 – Robustez y producto

16. **Manejo de errores:** PS3838 (línea cerrada, odds, rate limit); Telegram (reconexión); guardrails y mensajes claros en UI.
17. **Mejora de match resolution:** Cache de fixtures, alias de equipos, umbrales de confidence.
18. **Documentación:** Actualizar `templates.md`, referencias a grafos reutilizables (ps3838_engine, etc.), enlaces a PS3838 API y Telethon.

---

### Estado de implementación (cierre por fases)

- **Fase 1 – Completada.** ExternalDataSource con `connector_type` ps3838 y telegram; CRUD por usuario (GET filtrado por `created_by`, POST crear); cliente PS3838 y nodos; match resolution; template y compiler `telegram_tipster_ps3838` registrados.
- **Fase 2 – Completada.** Flujo de conexión Telegram (send_code, sign_in, get_dialogs, save_connection); parser y Vision (openai_extract_tip); listener Telethon en `app.core.telegram.listener` (crea TipIntent PENDING); Execution Graph con guardrails (risk_check, odds_still_valid, place_bet_ps3838).
- **Fase 3 – Completada.** Pipeline tip: mensaje → parse/Vision → TipIntent (PENDING); APIs REST TipIntents (list, get, create, resolve, approve, reject, execute); dashboard backend (listado y summary por estrategia). L2/WebSocket para “tips en lectura” en tiempo real queda opcional.
- **Fase 4 – Completada.** UI Cuentas: crear conexión PS3838 (formulario nombre, usuario, contraseña); flujo “Conectar Telegram” (teléfono → código → dialogs → checkboxes → guardar). Template en selector; formulario de estrategia con SELECT PS3838 y Telegram; dashboard de tips en `/strategies/[id]/tips` con acciones y resumen.
- **Fase 5 – Completada.** Manejo de errores y reconexión documentado en §5.3.1; match resolution con confidence y mejoras iterativas descritas en §7; documentación y referencias en §13. Mejoras operativas (cache fixtures, alias) quedan como iteración futura.

---

## 12. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| **Match incorrecto (apostar al partido equivocado)** | Confidence score; modo "preguntar"; opción de elegir manualmente entre candidatos; logs y auditoría. |
| **Cuenta PS3838 no financiada** | La API requiere cuenta financiada; avisar en UI si el acceso falla por este motivo. |
| **Rate limits PS3838** | Snapshot 1/60 s por deporte, delta 1/5 s; cachear fixtures/odds y no abusar de llamadas. |
| **Telegram (Telethon userbot)** | Solo lectura; no enviar mensajes ni unirse masivamente; sesión encriptada; riesgo bajo de ban si uso moderado. |
| **Sesión Telethon revocada frecuentemente** | Educar al usuario: "No termines sesión en Ajustes > Dispositivos de Telegram"; ofrecer reconexión rápida vía modal; fallback temporal a modo manual (sin listener) si falla hasta que reconecte. |
| **OpenAI Vision** | API key por entorno; coste ~0.3–1 céntimo/imagen con gpt-4o-mini; no persistir imágenes, solo JSON extraído. |
| **Credenciales API** | Usuario/contraseña PS3838 y sesión Telethon encriptados (Fernet o patrón wallets); nunca en logs; acceso solo para el usuario dueño. |

---

## 13. Referencias

- [Near-Resolution Strategy Implementation Plan](near_resolution_strategy_implementation_plan.md) – L1/L2, intents, risk, UI.
- [Execution Engine](../architecture/execution-engine.md) – ExecutionPlan, plataformas.
- [Strategy Templates](templates.md) – Añadir plantilla "Telegram Tipsters → PS3838".
- [PS3838 API](https://ps3838api.github.io/) · [Getting Started](https://ps3838api.github.io/GettingStarted.html) · [Lines API](https://ps3838api.github.io/docs?api=lines) · [FAQs](https://ps3838api.github.io/FAQs.html) · [OpenAPI betsapi.yaml](https://raw.githubusercontent.com/ps3838api/api-spec/master/OpenAPI/betsapi.yaml).
- [Telethon](https://docs.telethon.dev/) – cliente MTProto para sesión de usuario y listener `NewMessage`.
- OpenAI API (Vision / gpt-4o, gpt-4o-mini) para extracción de tips desde imágenes.
