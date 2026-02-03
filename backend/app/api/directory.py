"""
Directory API — Phase 1.

Endpoints de lectura cache-first: categories, tags, markets, events.
Solo lee de DB; no llama a Gamma en la request.
Todas las respuestas incluyen meta de freshness (last_scanned_at, freshness, source, data_age_seconds).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.auth import get_current_user, User
from app.core.directory.service import DirectoryService

router = APIRouter(tags=["directory"])


def _meta(request: Request) -> Dict[str, Any]:
    """Meta de freshness para respuestas Directory."""
    scanner = getattr(request.app.state, "scanner", None)
    return DirectoryService.get_meta(scanner)


@router.get("/meta")
async def get_directory_meta(request: Request) -> Dict[str, Any]:
    """
    Meta del Directory: last_scanned_at, freshness, source, data_age_seconds.
    Phase 0/1: solo lectura desde app.state.scanner; no usa Gamma.
    """
    meta = _meta(request)
    return {
        "last_scanned_at": meta["last_scanned_at"],
        "freshness": meta["freshness"],
        "source": meta["source"],
        "data_age_seconds": meta["data_age_seconds"],
    }


@router.get("/categories")
async def get_directory_categories(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Lista categorías distintas desde DB (solo lectura Directory)."""
    categories = DirectoryService.get_categories(db)
    return {"items": categories, "total": len(categories), "_meta": _meta(request)}


@router.get("/tags")
async def get_directory_tags(
    request: Request,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Lista tags desde DB con paginación."""
    items, total = DirectoryService.get_tags(db, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset, "_meta": _meta(request)}


@router.get("/markets")
async def get_directory_markets(
    request: Request,
    category: Optional[str] = Query(None),
    tag_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    state: Optional[str] = Query(None, description="Filtrar markets que tengan al menos un event con este state"),
    next_days: Optional[int] = Query(None, description="Filtrar markets con event end_time en los próximos N días"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Lista markets desde DB con filtros y paginación. No llama a Gamma."""
    items, total = DirectoryService.get_markets(
        db,
        category=category,
        tag_id=tag_id,
        search=search,
        enabled=enabled,
        state=state,
        next_days=next_days,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset, "_meta": _meta(request)}


@router.get("/events")
async def get_directory_events(
    request: Request,
    market_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tag_id: Optional[str] = Query(None),
    next_days: Optional[int] = Query(None),
    max_time_to_resolution_minutes: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Lista events desde DB con filtros y paginación. No llama a Gamma."""
    items, total = DirectoryService.get_events(
        db,
        market_id=market_id,
        state=state,
        category=category,
        tag_id=tag_id,
        next_days=next_days,
        max_time_to_resolution_minutes=max_time_to_resolution_minutes,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset, "_meta": _meta(request)}
