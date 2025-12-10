"""
System configuration API endpoints.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.system_config import SystemConfig
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from app.core.config_service import config_service
from datetime import datetime

router = APIRouter(prefix="/system", tags=["system"])


class SystemConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None


@router.get("/config")
async def get_system_config(
    current_user: User = Depends(get_current_user),
):
    """Get all system configuration grouped by category."""
    db = SessionLocal()
    try:
        configs = db.query(SystemConfig).all()
        
        result = {
            "system": {},
            "scanner": {},
            "event_engine": {},
            "risk": {},
        }
        
        for config in configs:
            # Parse value based on type
            if config.value_type == "float":
                value = float(config.value)
            elif config.value_type == "int":
                value = int(config.value)
            elif config.value_type == "bool":
                value = config.value.lower() in ("true", "1", "yes")
            else:
                value = config.value
            
            if config.category in result:
                result[config.category][config.key] = value
        
        return result
    finally:
        db.close()


@router.get("/config/{key}")
async def get_config_value(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific configuration value."""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    
    # Parse value
    if config.value_type == "float":
        value = float(config.value)
    elif config.value_type == "int":
        value = int(config.value)
    elif config.value_type == "bool":
        value = config.value.lower() in ("true", "1", "yes")
    else:
        value = config.value
    
    return {
        "key": config.key,
        "value": value,
        "value_type": config.value_type,
        "category": config.category,
        "description": config.description,
    }


@router.put("/config/{key}")
async def update_config_value(
    key: str,
    update: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Update a configuration value (admin only)."""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    
    config.value = update.value
    if update.description:
        config.description = update.description
    config.updated_by = current_user.id
    config.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Invalidate cache
    config_service.invalidate_cache(key)
    
    return {"status": "updated"}

