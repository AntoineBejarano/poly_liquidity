"""
System configuration API endpoints.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db, SessionLocal
from app.models.system_config import SystemConfig
from app.models.decision_trace import DecisionTrace
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from app.core.config_service import config_service
from datetime import datetime

router = APIRouter(prefix="/system", tags=["system"])


class SystemConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None
    requires_confirmation: Optional[bool] = None  # Para confirmar cambios críticos


@router.get("/config")
async def get_system_config(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_metadata: bool = Query(True, description="Include metadata (is_readonly, requires_confirmation, etc.)"),
    current_user: User = Depends(get_current_user),
):
    """
    Get all system configuration grouped by category.
    
    Returns configuration with metadata (is_readonly, requires_confirmation, etc.)
    """
    db = SessionLocal()
    try:
        query = db.query(SystemConfig)
        if category:
            query = query.filter(SystemConfig.category == category)
        
        configs = query.all()
        
        result = {}
        
        for config in configs:
            # Parse value based on type
            if config.value_type == "float":
                value = float(config.value)
            elif config.value_type == "int":
                value = int(config.value)
            elif config.value_type == "bool":
                value = config.value.lower() in ("true", "1", "yes")
            elif config.value_type == "json":
                import json
                try:
                    value = json.loads(config.value)
                except:
                    value = config.value
            else:
                value = config.value
            
            if config.category not in result:
                result[config.category] = {}
            
            if include_metadata:
                result[config.category][config.key] = {
                    "value": value,
                    "value_type": config.value_type,
                    "description": config.description,
                    "is_readonly": config.is_readonly,
                    "requires_confirmation": config.requires_confirmation,
                    "min_value": config.min_value,
                    "max_value": config.max_value,
                    "validation_rule": config.validation_rule,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }
            else:
                result[config.category][config.key] = value
        
        return result
    finally:
        db.close()


class BetSizeConfigUpdate(BaseModel):
    """Configuración de tamaño de apuesta."""
    mode: str  # "percentage" | "fixed_range"
    percentage: Optional[float] = None  # Porcentaje del bank (cuando mode = "percentage")
    min_amount: Optional[float] = None  # Tamaño mínimo en USDC (cuando mode = "fixed_range")
    max_amount: Optional[float] = None  # Tamaño máximo en USDC (cuando mode = "fixed_range")


@router.put("/config/bet-size")
async def update_bet_size_config(
    config: BetSizeConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """
    Actualizar configuración de tamaño de apuesta.
    
    Los modos son mutuamente excluyentes:
    - "percentage": Usa porcentaje del bank (requiere 'percentage')
    - "fixed_range": Usa rango fijo (requiere 'min_amount' y 'max_amount')
    """
    # Validar modo
    if config.mode not in ["percentage", "fixed_range"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mode must be 'percentage' or 'fixed_range'"
        )
    
    # Validar según modo
    if config.mode == "percentage":
        if config.percentage is None or config.percentage <= 0 or config.percentage > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="percentage must be between 0 and 100 when mode is 'percentage'"
            )
        # Limpiar valores de fixed_range
        config.min_amount = None
        config.max_amount = None
    elif config.mode == "fixed_range":
        if config.min_amount is None or config.min_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_amount must be greater than 0 when mode is 'fixed_range'"
            )
        if config.max_amount is None or config.max_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_amount must be greater than 0 when mode is 'fixed_range'"
            )
        if config.min_amount > config.max_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_amount cannot be greater than max_amount"
            )
        # Limpiar valor de percentage
        config.percentage = None
    
    # Actualizar o crear configuraciones
    def update_or_create_config(key: str, value: Any, value_type: str, description: str):
        existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if existing:
            existing.value = str(value)
            existing.updated_by = current_user.id
            existing.updated_at = datetime.utcnow()
        else:
            new_config = SystemConfig(
                key=key,
                value=str(value),
                value_type=value_type,
                category="strategy",
                description=description,
                is_readonly=False,
                requires_confirmation=False,
                updated_by=current_user.id,
                updated_at=datetime.utcnow()
            )
            db.add(new_config)
    
    # Actualizar bet_size_mode
    update_or_create_config("bet_size_mode", config.mode, "string", "Modo de cálculo de tamaño de apuesta: 'percentage' o 'fixed_range'")
    
    # Actualizar valores según modo
    if config.mode == "percentage":
        update_or_create_config("bet_size_percentage", config.percentage, "float", "Porcentaje del bank a apostar por operación")
        # Eliminar configs de fixed_range si existen
        for key in ["bet_size_min", "bet_size_max"]:
            existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if existing:
                db.delete(existing)
    else:  # fixed_range
        update_or_create_config("bet_size_min", config.min_amount, "float", "Tamaño mínimo de apuesta en USDC")
        update_or_create_config("bet_size_max", config.max_amount, "float", "Tamaño máximo de apuesta en USDC")
        # Eliminar config de percentage si existe
        existing = db.query(SystemConfig).filter(SystemConfig.key == "bet_size_percentage").first()
        if existing:
            db.delete(existing)
    
    db.commit()
    
    # Reload config service
    config_service.load_from_db()
    
    return {
        "status": "updated",
        "bet_size_config": {
            "mode": config.mode,
            "percentage": config.percentage,
            "min_amount": config.min_amount,
            "max_amount": config.max_amount,
        }
    }


@router.get("/config/bet-size")
async def get_bet_size_config(
    current_user: User = Depends(get_current_user),
):
    """Obtener configuración actual de tamaño de apuesta."""
    mode = config_service.get("bet_size_mode", "fixed_range")
    percentage = config_service.get("bet_size_percentage")
    min_amount = config_service.get("bet_size_min")
    max_amount = config_service.get("bet_size_max")
    
    return {
        "mode": mode,
        "percentage": percentage,
        "min_amount": min_amount,
        "max_amount": max_amount,
    }


# ============================================================================
# FASE 0: MODO Y PROTECCIONES
# IMPORTANTE: Estos endpoints deben ir ANTES de /config/{key} para evitar conflictos de routing
# ============================================================================

@router.get("/config/execution-mode", operation_id="system_get_execution_mode")
async def get_execution_mode():
    """
    Obtener modo de ejecución actual.
    
    Fase 0: Verificar que el sistema está en modo seguro antes de tocar APIs.
    No requiere autenticación - es endpoint de verificación de sistema.
    """
    execution_mode = config_service.get_execution_mode()
    
    return {
        "execution_mode": execution_mode,
        "requires_confirmation": execution_mode == "LIVE",
        "safe_modes": ["DRY_RUN", "PAPER"],
        "is_safe": execution_mode in ["DRY_RUN", "PAPER"],
        "description": {
            "DRY_RUN": "Simulación completa, no se envían órdenes",
            "PAPER": "Paper trading, órdenes a wallet de prueba",
            "LIVE": "Trading real con dinero real (requiere confirmación)"
        }
    }


@router.get("/config/protected-parameters")
async def get_protected_parameters():
    """
    Listar parámetros protegidos y sus valores.
    
    Fase 0: Verificar que los parámetros críticos están correctamente configurados.
    No requiere autenticación - es endpoint de verificación de sistema.
    """
    db = SessionLocal()
    try:
        # Parámetros críticos que requieren protección
        protected_keys = [
            "allow_zero_checker",
            "quorum_base",
            "execution_mode",
            "latency_fail_mode",
            "min_feed_confidence",
            "max_global_exposure",
            "max_market_exposure"
        ]
        
        protected_params = {}
        for key in protected_keys:
            try:
                config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            except Exception:
                # Si la tabla no existe (tests sin DB), usar defaults
                config = None
            if config:
                # Parse value based on type
                if config.value_type == "float":
                    value = float(config.value)
                elif config.value_type == "int":
                    value = int(config.value)
                elif config.value_type == "bool":
                    value = config.value.lower() in ("true", "1", "yes")
                else:
                    value = config.value
                
                protected_params[key] = {
                    "value": value,
                    "value_type": config.value_type,
                    "description": config.description,
                    "is_readonly": config.is_readonly,
                    "requires_confirmation": config.requires_confirmation,
                    "category": config.category,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }
            else:
                # Default values
                defaults = {
                    "allow_zero_checker": {"value": False, "value_type": "bool"},
                    "quorum_base": {"value": 2, "value_type": "int"},
                    "execution_mode": {"value": "DRY_RUN", "value_type": "string"},
                    "latency_fail_mode": {"value": "PAUSE", "value_type": "string"},
                    "min_feed_confidence": {"value": 0.7, "value_type": "float"},
                    "max_global_exposure": {"value": 200000.0, "value_type": "float"},
                    "max_market_exposure": {"value": 10000.0, "value_type": "float"},
                }
                if key in defaults:
                    protected_params[key] = {
                        "value": defaults[key]["value"],
                        "value_type": defaults[key]["value_type"],
                        "description": f"Default value for {key}",
                        "is_readonly": False,
                        "requires_confirmation": key in ["allow_zero_checker", "execution_mode", "quorum_base"],
                        "category": "system",
                        "updated_at": None,
                    }
        
        return {
            "protected_parameters": protected_params,
            "critical_parameters": [
                "allow_zero_checker",
                "execution_mode",
                "quorum_base"
            ],
            "count": len(protected_params),
            "note": "Estos parámetros requieren confirmación explícita para cambios críticos",
            "timestamp": datetime.utcnow().isoformat()
        }
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
    """
    Update a configuration value (admin only).
    
    If requires_confirmation is True, the update must include requires_confirmation=True in the request.
    """
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    
    # Check if readonly
    if config.is_readonly:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Config key '{key}' is readonly and cannot be modified"
        )
    
    # Check if requires confirmation
    if config.requires_confirmation and not update.requires_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Config key '{key}' requires confirmation. Set requires_confirmation=True in the request."
        )
    
    # Validate value type
    try:
        if config.value_type == "float":
            float(update.value)
        elif config.value_type == "int":
            int(update.value)
        elif config.value_type == "bool":
            if update.value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                raise ValueError("Invalid boolean value")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid value type for {config.value_type}: {str(e)}"
        )
    
    # Validate min/max if present
    if config.min_value:
        try:
            min_val = float(config.min_value) if config.value_type == "float" else int(config.min_value)
            val = float(update.value) if config.value_type == "float" else int(update.value)
            if val < min_val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Value {val} is below minimum {min_val}"
                )
        except (ValueError, TypeError):
            pass
    
    if config.max_value:
        try:
            max_val = float(config.max_value) if config.value_type == "float" else int(config.max_value)
            val = float(update.value) if config.value_type == "float" else int(update.value)
            if val > max_val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Value {val} is above maximum {max_val}"
                )
        except (ValueError, TypeError):
            pass
    
    config.value = update.value
    if update.description:
        config.description = update.description
    config.updated_by = current_user.id
    config.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Reload config service
    config_service.load_from_db()
    
    return {"status": "updated", "key": key, "new_value": update.value}


# Decision Traces Endpoints

@router.get("/decision-traces")
async def get_decision_traces(
    trace_id: Optional[UUID] = Query(None, description="Filter by trace_id"),
    market_id: Optional[UUID] = Query(None, description="Filter by market_id"),
    component: Optional[str] = Query(None, description="Filter by component (scanner, strategy, risk, execution)"),
    decision_stage: Optional[str] = Query(None, description="Filter by decision_stage (SCAN, EVENT_CONFIRMATION, STRATEGY, RISK, EXECUTION)"),
    decision: Optional[str] = Query(None, description="Filter by decision (APPROVED, REJECTED, ADJUSTED, CANCELLED)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
):
    """
    Get decision traces with optional filters.
    
    Returns decision traces for explainability and debugging.
    """
    db = SessionLocal()
    try:
        query = db.query(DecisionTrace)
        
        if trace_id:
            query = query.filter(DecisionTrace.trace_id == trace_id)
        if market_id:
            query = query.filter(DecisionTrace.market_id == market_id)
        if component:
            query = query.filter(DecisionTrace.component == component)
        if decision_stage:
            query = query.filter(DecisionTrace.decision_stage == decision_stage)
        if decision:
            query = query.filter(DecisionTrace.decision == decision)
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(DecisionTrace.timestamp.desc())
        
        # Pagination
        total = query.count()
        traces = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "traces": [
                {
                    "id": str(trace.id),
                    "trace_id": str(trace.trace_id),
                    "session_id": str(trace.session_id) if trace.session_id else None,
                    "timestamp": trace.timestamp.isoformat(),
                    "component": trace.component,
                    "decision_stage": trace.decision_stage,
                    "market_id": str(trace.market_id) if trace.market_id else None,
                    "event_id": str(trace.event_id) if trace.event_id else None,
                    "decision_type": trace.decision_type,
                    "decision": trace.decision,
                    "reason": trace.reason,
                    "input_data": trace.input_data,
                    "output_data": trace.output_data,
                    "config_used": trace.config_used,
                    "latency_ms": trace.latency_ms,
                    "confidence_score": trace.confidence_score,
                    "extra_metadata": trace.extra_metadata,
                }
                for trace in traces
            ]
        }
    finally:
        db.close()


@router.get("/decision-traces/{trace_id}")
async def get_decision_trace_by_trace_id(
    trace_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get all decision traces for a specific trace_id.
    
    This returns the complete pipeline for a single decision (SCAN -> EVENT_CONFIRMATION -> STRATEGY -> RISK -> EXECUTION).
    """
    db = SessionLocal()
    try:
        traces = db.query(DecisionTrace).filter(
            DecisionTrace.trace_id == trace_id
        ).order_by(DecisionTrace.timestamp.asc()).all()
        
        if not traces:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No decision traces found for trace_id {trace_id}"
            )
        
        return {
            "trace_id": str(trace_id),
            "stages": [
                {
                    "id": str(trace.id),
                    "decision_stage": trace.decision_stage,
                    "component": trace.component,
                    "timestamp": trace.timestamp.isoformat(),
                    "decision": trace.decision,
                    "reason": trace.reason,
                    "input_data": trace.input_data,
                    "output_data": trace.output_data,
                    "config_used": trace.config_used,
                    "latency_ms": trace.latency_ms,
                    "confidence_score": trace.confidence_score,
                    "extra_metadata": trace.extra_metadata,
                }
                for trace in traces
            ]
        }
    finally:
        db.close()


@router.get("/decision-traces/market/{market_id}")
async def get_decision_traces_by_market(
    market_id: UUID,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
):
    """
    Get decision traces for a specific market.
    
    Useful for understanding all decisions made for a particular market.
    """
    db = SessionLocal()
    try:
        query = db.query(DecisionTrace).filter(
            DecisionTrace.market_id == market_id
        ).order_by(DecisionTrace.timestamp.desc())
        
        total = query.count()
        traces = query.offset(offset).limit(limit).all()
        
        return {
            "market_id": str(market_id),
            "total": total,
            "offset": offset,
            "limit": limit,
            "traces": [
                {
                    "id": str(trace.id),
                    "trace_id": str(trace.trace_id),
                    "timestamp": trace.timestamp.isoformat(),
                    "component": trace.component,
                    "decision_stage": trace.decision_stage,
                    "decision": trace.decision,
                    "reason": trace.reason,
                    "input_data": trace.input_data,
                    "output_data": trace.output_data,
                }
                for trace in traces
            ]
        }
    finally:
        db.close()



