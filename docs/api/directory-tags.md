# GET /directory/tags — Tags desde DB (legacy, no discovery)

**Importante:** La página `/markets` (discovery) **no** usa este endpoint. Usa **GET /api/polymarket/tags** (Gamma-first). Este endpoint es **legacy / interno**: solo lee de DB (tabla Tag). No es fuente de verdad para el UI de discovery. Ver `docs/implementation/DISCOVERY_VS_WALLET.md`.

## Uso legacy

- **Router:** `app/api/directory.py` (prefix `/directory`).
- **Llamada típica:** `GET /directory/tags?limit=200&offset=0` (requiere auth).

## Endpoint (backend)

- **Método y ruta:** `GET /directory/tags`
- **Prefijo:** El router Directory está montado con `prefix="/directory"`, así que la URL completa es:
  - `GET {BASE_URL}/directory/tags`
  - Ejemplo: `GET http://localhost:8000/directory/tags`

## Query params

| Parámetro | Tipo   | Default | Descripción        |
|-----------|--------|---------|--------------------|
| `limit`   | int    | 200     | Máximo items (1–500) |
| `offset`  | int    | 0       | Offset paginación  |

## Respuesta (200)

```json
{
  "items": [
    {
      "tag_id": "string",
      "polymarket_tag_id": "string | null",
      "name": "string",
      "slug": "string | null",
      "label": "string | null"
    }
  ],
  "total": 0,
  "limit": 200,
  "offset": 0,
  "_meta": {
    "last_scanned_at": "string | null",
    "freshness": "fresh | stale",
    "source": "db",
    "data_age_seconds": "number | null"
  }
}
```

- **items:** Lista de tags. El frontend usa `tag_id` y `name` para el desplegable.
- **total:** Número total de tags en DB.
- **_meta:** Metadatos de freshness del Directory (opcional para el dropdown).

## Origen de los datos (backend)

- **Solo lectura desde DB.** No se llama a Gamma en esta petición.
- Los ítems vienen de la tabla **Tag** (`app.models.tag`, tabla `tags`).
- Esa tabla se rellena cuando corre el **Scanner**, que ingesta markets desde Gamma y crea/actualiza Tag y MarketTag.
- Si el Scanner **no ha corrido** o **no ha ingesta do markets**, la tabla Tag puede estar **vacía** → `items: []` y el desplegable sale vacío.

## Alineación frontend ↔ backend

- El frontend espera `res.items` como array y usa `tag_id` y `name`. El backend devuelve exactamente eso, así que el contrato está alineado.
- Si el desplegable está vacío, la causa habitual es **Tag table vacía** (Scanner no ejecutado o sin datos ingesta dos), no un desajuste de contrato.

## Cómo tener datos en el desplegable

1. **Backend:** Ejecutar el Scanner para ingestar markets desde Gamma y poblar Tag (y MarketTag). Revisar cómo se arranca el Scanner en tu despliegue (boot, cron, comando, etc.).
2. **Frontend (fallback):** Si `GET /directory/tags` devuelve `items: []`, la página puede intentar obtener tags a partir de **GET /markets** (los markets devuelven un array `tags` por market) y rellenar el dropdown con esos tags derivados hasta que el Directory tenga datos.

## Referencias en código

- Backend: `app/api/directory.py` → `get_directory_tags`; `app/core/directory/service.py` → `DirectoryService.get_tags`.
- Frontend: `app/markets/page.tsx` (useEffect que llama a `/directory/tags` y el fallback que deriva de `data?.markets`).
