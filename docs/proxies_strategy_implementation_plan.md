# Plan de implementación: Proxies en DB y asignación por estrategia

**Objetivo:** Un usuario declara N proxies en su cuenta (en un menú dedicado "Proxies"). Luego, al crear/editar una estrategia que usa varias conexiones (ej. Telegram y PS3838), el usuario puede elegir:

1. **Ningún proxy** (fallback: el tráfico sale por el servidor/cloud)
2. **Un proxy para todas las conexiones**
3. **Un proxy por conexión** (un proxy para Telegram y otro para PS3838)
4. **(Opcional)** Mezcla: un proxy global + override solo para una conexión

Los proxies **no** se asignan a las cuentas (ExternalDataSource, wallets, etc.); la asignación es explícita en la **configuración de la estrategia**.

**Última actualización:** 2026-02.

---

## 1. Entidades (modelo mental)

### Proxies (recurso de usuario)

- Cada usuario tiene una lista de proxies con:
  - Tipo (SOCKS5 / HTTP / MTProto según aplique)
  - Estado (healthy / unhealthy / unknown)
  - Latencia / última validación
  - etc.
- Se gestionan **solo** desde **Sidebar → Proxies** (CRUD).
- El editor de estrategia **solo consume** la lista de proxies para permitir selección (no crea/edita proxies).

### Cuentas (recurso de usuario)

- Cada usuario tiene N cuentas por conector (Telegram accounts, PS3838 accounts, Polymarket wallets, etc.).
- Se gestionan desde **Sidebar → Cuentas** (como hoy).
- En la estrategia, el usuario elige qué cuenta usar para cada conexión.
- **Separación clara:** Proxies y Cuentas son independientes; los proxies no se asignan a las cuentas.

---

## 2. Persistencia en Strategy (modelo)

En `strategies` se guardan dos campos:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `proxy_id` | UUID nullable | Proxy "global" para toda la estrategia. |
| `connection_proxies` | JSONB NOT NULL, default `{}` | Mapa `connection_key → proxy_id`. Ejemplo: `{ "telegram": "proxy-uuid-1", "ps3838": "proxy-uuid-2" }` |

**A) Default y normalización**

- En migración: `connection_proxies` con default `{}` y **NOT NULL**.
- En backend: siempre normalizar a `{}` (nunca persistir `null`). Así se evita chequear `null` vs `{}` por todas partes.

**B) Normalización de keys: `connection_key` canónico**

El `connection_key` es un **string canónico** (enum conceptual). Usar siempre minúsculas sin guiones ni espacios. Claves válidas (lista cerrada, extendible según conectores):

- `telegram`
- `ps3838`
- `polymarket`
- `pinnacle`
- (añadir según nuevos conectores)

Si no se fija esto, aparecerán variantes (`ps3838`, `PS3838`, `ps-3838`, etc.) y el runtime "no encontrará" el override. El backend debe rechazar keys desconocidas (ver §5).

### Precedencia / resolución en runtime

Para construir el cliente de cada conexión (`connection_key`):

1. Si existe `connection_proxies[connection_key]` → usar ese proxy  
2. Si no existe → si `proxy_id` está seteado → usar `proxy_id`  
3. Si no hay proxy → usar salida cloud (sin proxy)

Esto implementa: ninguno / uno para ambas / uno por cada / mezcla (global + override).

### Ejemplo concreto (Telegram → PS3838)

| Modo | `proxy_id` | `connection_proxies` | Runtime |
|------|------------|----------------------|---------|
| Sin proxy | `null` | `{}` | Telegram y PS3838 salen por cloud |
| Un proxy para todas | `proxy_X` | `{}` | Ambos salen por proxy_X |
| Un proxy por conexión | `null` | `{"telegram":"proxy_A","ps3838":"proxy_B"}` | Telegram → proxy_A, PS3838 → proxy_B |
| Mezcla (global + override) | `proxy_X` | `{"telegram":"proxy_A"}` | Telegram → proxy_A, PS3838 → proxy_X |

---

## 3. Modelo de datos: tabla `proxies`

### 3.1 Campos

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `id` | UUID | Sí (PK) | Identificador único (generado). |
| `name` | String | Sí | Nombre descriptivo (ej. "Proxy EU Polymarket", "Mobile ES"). |
| `proxy_type` | String | Sí | `SOCKS5` (default), `HTTP`, `MTProto`. |
| `proxy_host` | String | Sí | IP o hostname. |
| `proxy_port` | Integer | Sí | Puerto (ej. 1080 SOCKS5, 8080 HTTP). |
| `proxy_username` | String | No | Usuario para autenticación. |
| `encrypted_proxy_password` | LargeBinary | No | Contraseña encriptada (mismo mecanismo que wallets). |
| `proxy_country` | String | No | País preferido (para mobile proxies). |
| `validation_status` | String | No | `healthy`, `unhealthy`, `unknown`. |
| `last_validation_at` | DateTime | No | Última vez que se validó el proxy. |
| `validation_latency_ms` | Integer | No | Latencia en ms de la última validación (informativo). |
| `created_by` | String (FK) | No | `neon_auth.users_sync.id`. |
| `created_at` | DateTime | Sí | |
| `updated_at` | DateTime | Sí | |

### 3.2 Consideraciones

- **Encriptación:** Mismo servicio/util que usa el proyecto para wallets.
- **Índices:** `created_by`, `validation_status` para listados.
- **Validación:** Endpoint `POST /proxies/{id}/validate` hace una conexión de prueba y actualiza `last_validation_at`, `validation_status` y `validation_latency_ms`.

---

## 4. API: Proxies

### 4.1 Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/proxies` | Lista proxies del usuario con status/latencia (sin secretos). |
| POST | `/proxies` | Crear proxy (password en claro, backend encripta). |
| GET | `/proxies/{id}` | Detalle de un proxy (sin contraseña). |
| PUT | `/proxies/{id}` | Actualizar proxy (password opcional). |
| DELETE | `/proxies/{id}` | Eliminar proxy (ver regla de borrado abajo). |
| POST | `/proxies/{id}/validate` | Probar conectividad; actualizar status y latencia. |

### 4.2 Regla de borrado (igual que Cuentas)

- El borrado se hace **solo** desde el menú UI de Proxies. No existe borrado desde la estrategia.
- Si el proxy está referenciado por **alguna estrategia activa**, **NO** se puede borrar.
- "En uso" son dos casos:
  1. `strategies.proxy_id = :proxy_id AND strategies.is_active = true`
  2. `strategies.connection_proxies` contiene `:proxy_id` en alguno de sus **valores** AND `strategies.is_active = true`

**Implementación del check JSONB (Postgres):**

El segundo caso requiere consultar si algún valor del JSONB coincide con el `proxy_id`. Consulta eficiente:

```sql
SELECT 1 FROM strategies
WHERE is_active = true
  AND (
    proxy_id = :proxy_id
    OR EXISTS (
      SELECT 1 FROM jsonb_each_text(connection_proxies) AS kv
      WHERE kv.value = :proxy_id::text
    )
  )
LIMIT 1;
```

- Asegurar índice en `strategies (is_active)`. Para `connection_proxies` la consulta con `jsonb_each_text` es la opción estándar; si el volumen de estrategias activas es alto, valorar cachear la lista de proxy_ids en uso.
- En caso de rechazo, devolver error: **"Proxy en uso por estrategia(s) activa(s)"**.

### 4.3 GET /proxies – filtros para alimentar selects

- `GET /proxies` lista proxies del usuario (sin secretos).
- **Filtros típicos:**
  - `?include_inactive=false` (default: solo activos; o equivalente si se añade `is_active` al modelo).
  - `?status=healthy` (opcional): filtrar por `validation_status` para UX más limpia.
- Respuesta: `id`, `name`, `proxy_type`, `proxy_host`, `proxy_port`, `proxy_country`, `validation_status`, `last_validation_at`, `validation_latency_ms`.

---

## 5. API: Estrategias – validación backend (importante)

- Strategy create/update acepta `proxy_id` y `connection_proxies`.
- **Validaciones obligatorias (aunque no bloquees por unhealthy):**
  1. **proxy_id (global y por conexión):** Todos los `proxy_id` referenciados deben existir y pertenecer al usuario. Si no → rechazar con error claro.
  2. **connection_proxies – keys canónicas:** Si llega `connection_proxies` con keys desconocidas (no están en el enum de `connection_key` válidos: `telegram`, `ps3838`, `polymarket`, `pinnacle`, etc.) → **rechazar** con error claro: **"connection_key inválida: {key}"**. Así se evita basura en DB.
- **NO** bloquear el guardado si el proxy está unhealthy; el usuario ya lo ve en Proxies. La estrategia solo selecciona.

---

## 6. UI: Sidebar y menú

### 6.1 Sidebar

- **Proxies:** Pantalla para crear/editar/eliminar proxies + ver estado/latencia.
- **Cuentas:** Pantalla para crear/editar/eliminar cuentas por conector (como hoy).

---

## 7. UI: Gestión de Proxies (Sidebar → Proxies)

### 7.1 Ubicación

- Página: **`/settings/proxies`** o **`/proxies`** (según estructura del sidebar).
- Enlace en sidebar: "Proxies".

### 7.2 Listado

- Tabla: **Nombre**, **Tipo** (SOCKS5/HTTP/MTProto), **Host:Puerto**, **País**, **Estado** (healthy/unhealthy/unknown), **Latencia** (ms, última validación), **Acciones** (Editar, Eliminar, Validar).
- Botón "Agregar proxy".

### 7.3 Formulario crear/editar

| Campo | Tipo en UI | Obligatorio | Notas |
|-------|------------|-------------|--------|
| Nombre | Text | Sí | Identificador en listas y desplegables. |
| proxy_type | SELECT | Sí | SOCKS5 (default), HTTP, MTProto. |
| proxy_host | Text | Sí | IP o hostname. |
| proxy_port | Number | Sí | Ej. 1080 (SOCKS5), 8080 (HTTP). |
| proxy_username | Text | No | Para auth. |
| proxy_password | Password | No | En creación/edición; opcional al editar ("Nueva contraseña"). |
| proxy_country | SELECT | No | Lista de países (para mobile proxies). |

---

## 8. UI: Formulario de Estrategia (ejemplo Telegram + PS3838)

### 8.1 Estructura del formulario

La estrategia tiene secciones:

#### Sección: Conexiones / Cuentas

- "Cuenta de Telegram" → dropdown con las cuentas Telegram del usuario.
- "Cuenta de PS3838" → dropdown con las cuentas PS3838 del usuario.

#### Sección: Proxies (routing)

Un **control de modo** (radio o select) con **3 opciones**:

1. **Sin proxy** (usar cloud)
2. **Un proxy para todas las conexiones**
3. **Un proxy por conexión**

### 8.2 Comportamiento según modo

| Modo | Dropdowns mostrados |
|------|---------------------|
| **Sin proxy** | No se muestra ningún dropdown de proxy (o se muestran deshabilitados). |
| **Un proxy para todas** | Un dropdown: **"Proxy (todas las conexiones)"** (lista de proxies del usuario). |
| **Un proxy por conexión** | Un dropdown por conexión: **"Proxy para Telegram"**, **"Proxy para PS3838"**. |

### 8.3 Lista de proxies en dropdowns (lo mínimo para que sea clarísimo)

- La lista viene de `GET /proxies` (del usuario), con filtros opcionales (`?status=healthy`, etc.).
- **Label de cada opción:** `name — status — latency_ms`  
  Ejemplo: `Mobile ES — unhealthy — 820ms`  
  (sin bloquear selección; es informativo).
- **Link pequeño "Ver detalles"** junto al dropdown que abre `/proxies` en otra pestaña. Así se mantiene la filosofía (diagnóstico en Proxies) sin selecciones a ciegas.
- **Regla UX:** NO bloquear el guardado si el proxy está unhealthy. El usuario lo ve en el label y puede ir a Proxies; la estrategia solo selecciona.

### 8.4 Mapeo UI → persistencia

| Modo elegido | `proxy_id` | `connection_proxies` |
|--------------|------------|----------------------|
| Sin proxy | `null` | `{}` |
| Un proxy para todas | `proxy_X` | `{}` |
| Un proxy por conexión | `null` | `{"telegram":"proxy_A","ps3838":"proxy_B"}` |
| Mezcla (opcional) | `proxy_X` | `{"telegram":"proxy_A"}` (override solo Telegram) |

---

## 9. Qué NO se quiere (importante)

- **NO** asignar proxies por defecto a cuentas (ExternalDataSource, wallets, telegram accounts). La asignación del proxy es explícita en la estrategia.
- **NO** bloquear el guardado de la estrategia por proxy unhealthy. El usuario ya lo ve en Proxies. La estrategia solo selecciona.
- **NO** permitir borrar un proxy desde la estrategia; solo desde el menú Proxies.

---

## 10. Backend: Uso del proxy en conexiones

### 10.1 Servicio de resolución

- Dado `strategy_id` y `connection_key` (ej. `telegram`, `ps3838`, `polymarket`):
  1. Si `connection_proxies[connection_key]` existe → usar ese `proxy_id`.
  2. Si no → si `proxy_id` existe → usar `proxy_id`.
  3. Si no hay proxy → devolver `None` (salida cloud).

### 10.2 Integración en clientes

- **Polymarket / HTTP:** Configurar proxy en httpx/aiohttp.
- **Telegram (Telethon):** Pasar proxy (SOCKS5, MTProto) al cliente.
- **PS3838 / Pinnacle:** Inyectar proxy en sesión HTTP.

### 10.3 Validación

- `POST /proxies/{id}/validate`: según `proxy_type`, probar conectividad, actualizar `last_validation_at`, `validation_status`, `validation_latency_ms`.
- No bloquear creación/edición de estrategia por proxy unhealthy.

### 10.4 Runtime: fallo de resolución

Definir explícitamente qué pasa si:

1. **Strategy apunta a un proxy borrado** (no debería ocurrir por la regla de borrado, pero puede pasar con datos legacy).
2. **Proxy existe pero faltan host/port** (datos corruptos).

**Comportamiento recomendado:** Loggear el fallo (sin secretos: strategy_id, connection_key, proxy_id) y tratarlo como `None` → **cloud fallback**. No tumbar la estrategia; la conexión sale por cloud.

---

## 11. Migraciones (Alembic)

- **Tabla `proxies`:** Crear con todos los campos descritos en §3. Incluye `created_by` (FK a `neon_auth.users_sync.id`) para scope por usuario: una sola tabla multi-tenant, cada fila pertenece a un usuario. La migración crea la tabla; no hace falta tabla separada por usuario.
- **Tabla `strategies`:** Añadir:
  - `proxy_id` (UUID nullable, FK a `proxies.id`)
  - `connection_proxies` (JSONB **NOT NULL**, default `'{}'`)

---

## 12. Resumen de tareas (checklist)

- [ ] **DB:** Modelo `Proxy` y migración tabla `proxies` (con `created_by` para multi-tenant).
- [ ] **DB:** En `strategies` añadir `proxy_id` y `connection_proxies` (JSONB NOT NULL, default `{}`).
- [ ] **Backend:** API CRUD `/proxies` + `validate`; filtros `include_inactive`, `status`.
- [ ] **Backend:** Regla de borrado con query JSONB eficiente (check proxy_id en uso por estrategias activas).
- [ ] **Backend:** Strategy create/update: validar proxy_ids existan y pertenezcan al usuario; rechazar connection_keys inválidas.
- [ ] **Backend:** Normalizar `connection_proxies` a `{}` siempre; nunca persistir null.
- [ ] **Backend:** Servicio de resolución strategy + connection_key → proxy config; fallback a cloud si proxy borrado/corrupto (log sin secretos).
- [ ] **Backend:** Inyectar proxy en clientes (Polymarket, Telegram, PS3838, etc.).
- [ ] **Frontend:** Página Sidebar → Proxies (listado + CRUD + estado/latencia).
- [ ] **Frontend:** Formulario de estrategia: control de modo y dropdowns; label `name — status — latency_ms` + link "Ver detalles" → /proxies.
- [ ] **Docs:** Actualizar documentación de estrategias (telegram_tipster_ps3838, etc.).
