"""
State Cache API endpoints.

APIs para consultar el State Cache (solo lectura, para debugging/monitoring).
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.api.auth import get_current_user, User
from app.models.state_cache import StateCache

router = APIRouter(prefix="/state-cache", tags=["state-cache"])


class StateCacheResponse(BaseModel):
    """Modelo de respuesta para entrada de State Cache."""
    id: str
    cache_key: str
    cache_value: dict
    strategy_id: Optional[str]
    event_id: Optional[str]
    expires_at: Optional[str]
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


def cache_entry_to_dict(entry: StateCache) -> dict:
    """Convierte un modelo StateCache a diccionario."""
    return {
        "id": str(entry.id),
        "cache_key": entry.cache_key,
        "cache_value": entry.cache_value,
        "strategy_id": str(entry.strategy_id) if entry.strategy_id else None,
        "event_id": str(entry.event_id) if entry.event_id else None,
        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


@router.get("", response_model=List[StateCacheResponse])
async def get_state_cache(
    strategy_id: Optional[UUID] = Query(None, description="Filter by strategy_id"),
    event_id: Optional[UUID] = Query(None, description="Filter by event_id"),
    pattern: Optional[str] = Query(None, description="Search by key pattern (simple wildcard)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene valores del State Cache.
    
    Solo lectura - para debugging y monitoring.
    El State Cache se actualiza automáticamente por Support Graphs.
    """
    query = db.query(StateCache)
    
    if strategy_id:
        query = query.filter(StateCache.strategy_id == strategy_id)
    if event_id:
        query = query.filter(StateCache.event_id == event_id)
    if pattern:
        # Búsqueda simple por patrón (wildcard básico)
        # Reemplazar * con % para SQL LIKE
        pattern_sql = pattern.replace("*", "%")
        query = query.filter(StateCache.cache_key.like(pattern_sql))
    
    # Filtrar entradas expiradas
    from datetime import datetime
    query = query.filter(
        (StateCache.expires_at.is_(None)) | (StateCache.expires_at > datetime.utcnow())
    )
    
    cache_entries = query.order_by(StateCache.created_at.desc()).limit(limit).offset(offset).all()
    
    return [cache_entry_to_dict(e) for e in cache_entries]


@router.get("/{cache_key:path}")
async def get_state_cache_by_key(
    cache_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene un valor específico del State Cache por su clave."""
    entry = db.query(StateCache).filter(StateCache.cache_key == cache_key).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cache entry not found"
        )
    
    # Verificar si está expirado
    from datetime import datetime
    if entry.expires_at and entry.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cache entry expired"
        )
    
    return cache_entry_to_dict(entry)

