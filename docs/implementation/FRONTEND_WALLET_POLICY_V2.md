# Frontend alineado con política v2 (wallet por usuario, FAIL CLOSED)

El backend sigue la **política institucional v2.0**: no existe CLOB global ni system wallet; toda operación wallet-data exige `user_id` + wallet en BD. FAIL CLOSED.

Este documento describe cómo el frontend está alineado con esa política.

---

## 1) No asumir wallet global ni env

- El frontend **no** muestra ni usa `PRIVATE_KEY`/`FUNDER` de entorno. Las credenciales CLOB son siempre por usuario (wallet en BD).
- La única forma de “tener wallet” para el usuario es **configurarla en Ajustes → Wallets** (se guarda cifrada en backend por usuario).
- No hay UI que sugiera “configurar PRIVATE_KEY en .env” ni “system wallet”.

---

## 2) Rutas que pueden devolver 409 (WALLET_NOT_CONFIGURED)

El backend devuelve **409** con `detail.error === "WALLET_NOT_CONFIGURED"` cuando:

- `GET /api/polymarket/balance`
- Cualquier endpoint que use `_require_clob_client`: orders, trades, place, cancel, WS USER subscribe, connection status, test-auth.

El frontend debe:

- **Detectar 409** (por ejemplo con `ApiResponseError` y `WALLET_NOT_CONFIGURED_STATUS` en `lib/api.ts`).
- **No** tratar 409 como error genérico de red; mostrar mensaje claro: “User wallet not configured” / “No hay wallet configurada”.
- Ofrecer **enlace a Ajustes → Wallets** cuando aplique (p. ej. en Strategy Live al cargar balance).

---

## 3) Comportamiento por pantalla

| Pantalla / flujo | Alineación |
|------------------|------------|
| **Markets** | Usa `/markets` (directorio) y opcionalmente orderbook-metrics. No exige wallet para listar mercados. |
| **Dashboard / Capital** | `GET /dashboard` devuelve 200 con `equity: 0` si el usuario no tiene wallet (no devuelve 409). El frontend puede mostrar 0 sin error. |
| **Strategy Live** | `GET /api/polymarket/balance` puede devolver **409**. El frontend detecta 409, pone `walletNotConfigured` y muestra un aviso con enlace a **Ajustes → Wallets**. |
| **Settings → Wallets** | Formulario para añadir/activar wallet por usuario (label, address, private_key). Se envía al backend y se guarda cifrada por usuario. No hay “wallet de sistema”. |
| **Crear estrategia** | Lista de wallets del usuario (`/wallets?venue=polymarket`). Si no hay wallets, se muestra “No hay wallets configuradas” con enlace a configurar. |

---

## 4) Constantes y tipos en frontend

- **`lib/api.ts`**: `WALLET_NOT_CONFIGURED_STATUS = 409` para comparar con `ApiResponseError.statusCode`.
- Donde se llame a balance u otros endpoints wallet-data, capturar `ApiResponseError` y, si `statusCode === WALLET_NOT_CONFIGURED_STATUS`, mostrar mensaje y enlace a wallets.

---

## 5) Referencias

- Backend: `app/api/errors.py` (`WALLET_NOT_CONFIGURED_STATUS`, `wallet_not_configured()`).
- Backend: `app/api/polymarket.py` (`_require_clob_client`).
- Doc: `BOOT_VS_RUNTIME.md`, `PLAN_WALLET_SCOPE_REFACTOR.md`.
