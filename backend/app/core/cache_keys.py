"""
Canonicalización de queries para keys de cache (Plan Redis L2 Fase 4).

Mismas queries con distinto orden en arrays o params equivalentes (incl. defaults)
producen la misma key. Key final: gamma:markets:q:{sha256(canonical)}.
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional


# Defaults que aplican si el param no viene (deben coincidir con Query defaults en GET /markets)
_DEFAULTS = {
    "limit": 50,
    "offset": 0,
    "order": "createdAt",
    "ascending": False,
    "closed": "false",
}


def _norm_bool(v: Any) -> str:
    """Normaliza booleano a 'true' o 'false'."""
    if v is None:
        return "false"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return "true" if v.lower() in ("true", "1", "yes") else "false"
    return "true" if v else "false"


def _norm_array(v: Any) -> list[str]:
    """Convierte a lista de strings, dedupe y ordena."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        out = [str(x).strip() for x in v if x is not None and str(x).strip()]
        return sorted(dict.fromkeys(out))
    return sorted(dict.fromkeys([str(v).strip()])) if str(v).strip() else []


def canonicalize_markets_query(params: dict[str, Any]) -> str:
    """
    Normaliza los query params de /markets a un string canónico determinístico.

    - Aplica defaults para limit, offset, order, ascending, closed.
    - Normaliza booleans (true/false, 1/0 → "true"|"false").
    - Dedupe + sort en arrays: id, slug, clob_token_ids (keys pueden ser id[], slug[], etc.).
    - Omite params vacíos/null (tag_id, search, etc. si no vienen).
    - Normaliza rangos min/max si existen.
    - Salida: key=value ordenados alfabéticamente, separados por &.

    Solo incluye params que afectan la respuesta Gamma (o que definen la key de cache).
    """
    # Copia con defaults
    p = dict(_DEFAULTS)
    for k, v in params.items():
        if k in ("limit", "offset", "order", "closed", "ascending", "tag_id", "search",
                 "id", "slug", "clob_token_ids", "id[]", "slug[]", "clob_token_ids[]",
                 "liquidity_num_min", "liquidity_num_max", "volume_num_min", "volume_num_max",
                 "start_date_min", "start_date_max", "end_date_min", "end_date_max"):
            p[k] = v

    # Normalizar tipos
    out: list[tuple[str, str]] = []

    # Escalares con defaults
    out.append(("ascending", _norm_bool(p.get("ascending"))))
    out.append(("closed", (p.get("closed") or "false").strip().lower()))
    out.append(("limit", str(int(p.get("limit", _DEFAULTS["limit"])))))
    out.append(("offset", str(int(p.get("offset", _DEFAULTS["offset"])))))
    out.append(("order", (p.get("order") or _DEFAULTS["order"]).strip()))

    # tag_id: omitir si vacío
    tag_id = p.get("tag_id")
    if tag_id is not None and str(tag_id).strip():
        out.append(("tag_id", str(tag_id).strip()))

    # search: incluir en canonical para que key sea única por búsqueda (Fase 5 puede no cachear si existe)
    search = p.get("search")
    if search is not None and str(search).strip():
        out.append(("search", str(search).strip()))

    # Arrays: normalizar nombres id/slug/clob_token_ids (FastAPI puede enviar id[] como id)
    for key, key_alt in [("id", "id[]"), ("slug", "slug[]"), ("clob_token_ids", "clob_token_ids[]")]:
        arr = _norm_array(p.get(key) or p.get(key_alt))
        if arr:
            out.append((key, ",".join(arr)))

    # Rangos min/max (omitir si vacíos)
    for key in ("liquidity_num_min", "liquidity_num_max", "volume_num_min", "volume_num_max",
                "start_date_min", "start_date_max", "end_date_min", "end_date_max"):
        v = p.get(key)
        if v is not None and str(v).strip():
            out.append((key, str(v).strip()))

    # Ordenar por key y construir string
    out.sort(key=lambda x: x[0])
    return "&".join(f"{k}={v}" for k, v in out)


def build_markets_cache_key(params: dict[str, Any], *, key_prefix: str = "") -> str:
    """
    Construye la key de cache para GET /markets a partir de params canónicos.

    Key: {key_prefix}gamma:markets:q:{sha256(canonical)}.
    Si key_prefix está vacío, no se añade (el cache provider añade REDIS_KEY_PREFIX).
    """
    canonical = canonicalize_markets_query(params)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    prefix = (key_prefix.rstrip(":") + ":") if key_prefix else ""
    return f"{prefix}gamma:markets:q:{digest}"


# --- Fase 5: Buckets y TTL ---
# Bucket search: en v1 no cachear (cardinalidad). Alternativa futura: TTL ≤ 30s o heurística entropía.
BUCKET_SEARCH = "search"
BUCKET_NARROW = "narrow"
BUCKET_BROAD = "broad"

# TTL por bucket (soft_ttl; hard = soft + stale_grace en provider)
SOFT_TTL_BROAD_SEC = 90
SOFT_TTL_NARROW_SEC = 300
STALE_GRACE_MARKETS_SEC = 60


def _array_len(params: dict[str, Any], *keys: str) -> int:
    """Longitud del primer array no vacío entre keys (id, slug, clob_token_ids)."""
    for key in keys:
        for k in (key, key + "[]"):
            v = params.get(k)
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                return len([x for x in v if x is not None and str(x).strip()])
            return 1 if str(v).strip() else 0
    return 0


def get_markets_bucket(params: dict[str, Any]) -> str:
    """
    Bucket determinista para GET /markets (Fase 5).

    - search: param `search` existe (cualquier valor) → en v1 no cachear.
    - narrow: id[] o slug[] con length ≤ 20, o clob_token_ids[] con length ≤ 20.
    - broad: resto (solo filtros comunes: tag_id, closed, order, limit, offset, etc.).
    """
    if params.get("search") is not None and str(params.get("search", "")).strip():
        return BUCKET_SEARCH
    n_id = _array_len(params, "id")
    n_slug = _array_len(params, "slug")
    n_clob = _array_len(params, "clob_token_ids")
    if (n_id and n_id <= 20) or (n_slug and n_slug <= 20) or (n_clob and n_clob <= 20):
        return BUCKET_NARROW
    return BUCKET_BROAD


def should_cache_markets_v1(params: dict[str, Any]) -> bool:
    """
    v1: no cachear si existe param search (evita cardinalidad/entropía).
    Futuro: cachear search con TTL corto o heurística (len > 64, % no alfanum, etc.).
    """
    return get_markets_bucket(params) != BUCKET_SEARCH


def get_markets_soft_ttl_seconds(bucket: str) -> int:
    """Soft TTL en segundos por bucket. Hard = soft + STALE_GRACE_MARKETS_SEC en el provider."""
    if bucket == BUCKET_NARROW:
        return SOFT_TTL_NARROW_SEC
    if bucket == BUCKET_BROAD:
        return SOFT_TTL_BROAD_SEC
    # search: no cachear en v1; si se cachea en el futuro, devolver ej. 30
    return SOFT_TTL_BROAD_SEC
