"""
State Cache Service - Gestiona State Cache.

Support Graphs escriben aquí.
Decision Graph lee desde aquí.
"""
import logging
import re
import json
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.state_cache import StateCache

logger = logging.getLogger(__name__)


class StateCacheService:
    """
    Servicio para gestionar State Cache.
    
    Support Graphs escriben aquí.
    Decision Graph lee desde aquí.
    
    Implementa cache en dos niveles:
    1. Memoria (rápido, para hot path)
    2. Base de datos (persistente, para cold path)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._memory_cache: Dict[str, Tuple[Any, Optional[datetime]]] = {}  # cache_key -> (value, expires_at)
        
        # Detectar si estamos usando SQLite (necesita serialización JSON)
        from sqlalchemy import inspect
        engine = db.bind if hasattr(db, 'bind') else None
        if engine:
            self._is_sqlite = engine.dialect.name == 'sqlite'
        else:
            # Si no podemos detectar, asumir que no es SQLite (PostgreSQL)
            self._is_sqlite = False
    
    def _serialize_value(self, value: Any) -> Any:
        """Serializa un valor para guardarlo en la base de datos."""
        # Si es dict o list, serializar a JSON string
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value
    
    def _deserialize_value(self, value: Any) -> Any:
        """Deserializa un valor leído de la base de datos."""
        # Si es string y parece JSON, deserializar
        if isinstance(value, str):
            try:
                # Intentar parsear como JSON
                parsed = json.loads(value)
                return parsed
            except (json.JSONDecodeError, ValueError):
                # No es JSON, retornar como está
                return value
        return value
    
    async def get(self, cache_key: str) -> Optional[Any]:
        """
        Obtiene un valor del cache.
        
        Primero verifica memoria, luego DB.
        Si encuentra en DB, actualiza memoria.
        """
        now = datetime.utcnow()
        
        # Primero verificar memoria
        if cache_key in self._memory_cache:
            value, expires_at = self._memory_cache[cache_key]
            if expires_at is None or now < expires_at:
                return value
            else:
                # Expiró, eliminar de memoria
                del self._memory_cache[cache_key]
        
        # Luego verificar DB
        cache_entry = self.db.query(StateCache).filter(
            StateCache.cache_key == cache_key
        ).first()
        
        if cache_entry:
            # Verificar si expiró
            if cache_entry.expires_at is None or now < cache_entry.expires_at:
                # Deserializar valor si es necesario
                value = self._deserialize_value(cache_entry.cache_value)
                # Actualizar memoria
                self._memory_cache[cache_key] = (value, cache_entry.expires_at)
                return value
            else:
                # Expiró, eliminar de DB
                self.db.delete(cache_entry)
                self.db.commit()
        
        return None
    
    async def set(
        self,
        cache_key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        strategy_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None
    ):
        """
        Establece un valor en el cache.
        
        Actualiza memoria y DB.
        """
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        # Actualizar memoria
        self._memory_cache[cache_key] = (value, expires_at)
        
        # Serializar valor para guardarlo en DB (si es necesario)
        db_value = self._serialize_value(value) if self._is_sqlite else value
        
        # Actualizar DB
        cache_entry = self.db.query(StateCache).filter(
            StateCache.cache_key == cache_key
        ).first()
        
        if cache_entry:
            cache_entry.cache_value = db_value
            cache_entry.expires_at = expires_at
            cache_entry.updated_at = datetime.utcnow()
            if strategy_id:
                cache_entry.strategy_id = strategy_id
            if event_id:
                cache_entry.event_id = event_id
        else:
            cache_entry = StateCache(
                cache_key=cache_key,
                cache_value=db_value,
                expires_at=expires_at,
                strategy_id=strategy_id,
                event_id=event_id
            )
            self.db.add(cache_entry)
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing state cache entry: {e}", exc_info=True)
            raise
    
    async def get_many(self, pattern: str) -> Dict[str, Any]:
        """
        Obtiene múltiples valores usando un patrón.
        
        Soporta patrones como:
        - "event.{event_id}.*" - todos los valores para un evento
        - "strategy.{strategy_id}.*" - todos los valores para una estrategia
        - "event.*.market_state" - todos los market_state de eventos
        """
        # Convertir patrón a regex
        # "event.{event_id}.*" -> "event\..*\.*"
        # "event.*.market_state" -> "event\..*\.market_state"
        regex_pattern = pattern.replace(".", r"\.").replace("*", ".*").replace("{", "").replace("}", "")
        
        # Buscar en memoria primero
        memory_results = {}
        for key, (value, expires_at) in self._memory_cache.items():
            if re.match(regex_pattern, key):
                if expires_at is None or datetime.utcnow() < expires_at:
                    memory_results[key] = value
        
        # Buscar en DB
        db_results = {}
        cache_entries = self.db.query(StateCache).all()
        now = datetime.utcnow()
        
        for entry in cache_entries:
            if re.match(regex_pattern, entry.cache_key):
                if entry.expires_at is None or now < entry.expires_at:
                    # Deserializar valor si es necesario
                    value = self._deserialize_value(entry.cache_value)
                    db_results[entry.cache_key] = value
                    # Actualizar memoria si no está
                    if entry.cache_key not in memory_results:
                        self._memory_cache[entry.cache_key] = (value, entry.expires_at)
        
        # Combinar resultados (memoria tiene prioridad)
        result = {**db_results, **memory_results}
        return result
    
    async def delete(self, cache_key: str):
        """Elimina un valor del cache (memoria y DB)."""
        # Eliminar de memoria
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
        
        # Eliminar de DB
        cache_entry = self.db.query(StateCache).filter(
            StateCache.cache_key == cache_key
        ).first()
        
        if cache_entry:
            self.db.delete(cache_entry)
            self.db.commit()
    
    async def clear_expired(self):
        """Limpia entradas expiradas de memoria y DB."""
        now = datetime.utcnow()
        
        # Limpiar memoria
        expired_keys = [
            key for key, (_, expires_at) in self._memory_cache.items()
            if expires_at and now >= expires_at
        ]
        for key in expired_keys:
            del self._memory_cache[key]
        
        # Limpiar DB
        expired_entries = self.db.query(StateCache).filter(
            StateCache.expires_at.isnot(None),
            StateCache.expires_at <= now
        ).all()
        
        for entry in expired_entries:
            self.db.delete(entry)
        
        if expired_entries:
            self.db.commit()
            logger.info(f"Cleared {len(expired_entries)} expired cache entries from DB")

