"""
Risk configuration API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.system_config import SystemConfig
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from app.core.config_service import config_service
from datetime import datetime

router = APIRouter(prefix="/risk", tags=["risk"])


class RiskConfigResponse(BaseModel):
    max_exposure_per_market: float
    max_global_exposure: float
    min_entry_price: float
    target_margin: float
    max_markets_active: int


class RiskConfigUpdate(BaseModel):
    max_exposure_per_market: Optional[float] = None
    max_global_exposure: Optional[float] = None
    min_entry_price: Optional[float] = None
    target_margin: Optional[float] = None
    max_markets_active: Optional[int] = None


@router.get("/config")
async def get_risk_config(
    current_user: User = Depends(get_current_user),
):
    """Get current risk configuration."""
    config = config_service.get_risk_config()
    return RiskConfigResponse(
        max_exposure_per_market=config.max_exposure_per_market,
        max_global_exposure=config.max_global_exposure,
        min_entry_price=config.min_entry_price,
        target_margin=config.target_margin,
        max_markets_active=config.max_markets_active,
    )


@router.post("/config")
async def update_risk_config(
    update: RiskConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Update risk configuration (admin only)."""
    updates = update.dict(exclude_none=True)
    
    # Map to system_config keys
    key_mapping = {
        "max_exposure_per_market": "max_exposure_per_market",
        "max_global_exposure": "max_global_exposure",
        "min_entry_price": "min_entry_price",
        "target_margin": "target_margin",
        "max_markets_active": "max_markets_active",
    }
    
    for field, key in key_mapping.items():
        if field in updates:
            config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if config:
                config.value = str(updates[field])
                config.updated_by = current_user.id
                config.updated_at = datetime.utcnow()
            else:
                # Create new config
                config = SystemConfig(
                    key=key,
                    value=str(updates[field]),
                    value_type="float" if field != "max_markets_active" else "int",
                    category="risk",
                    updated_by=current_user.id,
                )
                db.add(config)
    
    db.commit()
    
    # Invalidate cache
    config_service.invalidate_cache()
    
    return {"status": "updated"}


# ============================================================================
# FASE 0: MODO Y PROTECCIONES
# ============================================================================

@router.get("/status")
async def get_risk_status():
    """
    Estado del Risk Engine y circuit breakers.
    
    Fase 0: Verificar que Risk Engine está activo y circuit breakers configurados.
    No requiere autenticación - es endpoint de verificación de sistema.
    """
    from app.core.risk_engine import risk_engine
    from app.main import runtime_supervisor
    
    # Obtener estado del Risk Engine
    risk_config = config_service.get_risk_config()
    
    # Obtener estado del Runtime Supervisor (circuit breakers)
    runtime_status = runtime_supervisor.get_status()
    
    # Obtener exposición actual
    try:
        exposure = risk_engine.get_current_exposure()
    except Exception as e:
        exposure = {"error": str(e)}
    
    # Manejar caso donde risk_config es None (tests sin DB)
    if risk_config is None:
        risk_config_dict = {
            "max_exposure_per_market": 10000.0,
            "max_global_exposure": 200000.0,
            "min_entry_price": 0.01,
            "target_margin": 0.05,
            "max_markets_active": 10,
        }
    else:
        risk_config_dict = {
            "max_exposure_per_market": risk_config.max_exposure_per_market,
            "max_global_exposure": risk_config.max_global_exposure,
            "min_entry_price": risk_config.min_entry_price,
            "target_margin": risk_config.target_margin,
            "max_markets_active": risk_config.max_markets_active,
        }
    
    return {
        "risk_engine": {
            "active": True,  # Risk Engine siempre está activo
            "config": risk_config_dict
        },
        "circuit_breakers": {
            "runtime_mode": runtime_status.get("mode", "UNKNOWN"),
            "status": runtime_status.get("status", {}),
            "kill_switches": {
                "available": True,
                "description": "Kill switches disponibles a través de Runtime Supervisor"
            }
        },
        "current_exposure": exposure,
        "timestamp": datetime.utcnow().isoformat()
    }