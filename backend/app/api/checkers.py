"""
Checkers and secrets API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.event_checker import EventChecker
from app.models.checker_config import CheckerConfig
from app.models.secret import Secret
from app.api.auth import get_current_user, get_admin_user
from app.api.auth import User
from app.core.secrets import secret_service
from app.core.checkers.registry import checker_registry
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/checkers", tags=["checkers"])


class CheckerCreate(BaseModel):
    implementation_key: str
    category: str
    name: str
    description: Optional[str] = None


class CheckerConfigCreate(BaseModel):
    secret_name: Optional[str] = None
    weight: float = 1.0
    timeout_seconds: float = 5.0
    enabled: bool = True


class SecretCreate(BaseModel):
    name: str
    value: str
    description: Optional[str] = None


@router.get("")
async def get_checkers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all checkers."""
    checkers = db.query(EventChecker).all()
    
    return [
        {
            "id": str(checker.id),
            "implementation_key": checker.implementation_key,
            "category": checker.category,
            "name": checker.name,
            "description": checker.description,
            "enabled": checker.enabled,
        }
        for checker in checkers
    ]


@router.post("")
async def create_checker(
    checker_data: CheckerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Create new checker (admin only)."""
    checker = EventChecker(
        implementation_key=checker_data.implementation_key,
        category=checker_data.category,
        name=checker_data.name,
        description=checker_data.description,
        enabled=True,
    )
    
    db.add(checker)
    db.commit()
    db.refresh(checker)
    
    return {
        "id": str(checker.id),
        "implementation_key": checker.implementation_key,
        "category": checker.category,
        "name": checker.name,
        "description": checker.description,
        "enabled": checker.enabled,
    }


@router.put("/{checker_id}")
async def update_checker(
    checker_id: UUID,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Update checker (admin only)."""
    checker = db.query(EventChecker).filter(EventChecker.id == checker_id).first()
    if not checker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checker not found")
    
    if enabled is not None:
        checker.enabled = enabled
        checker.updated_at = datetime.utcnow()
        db.commit()
    
    return {"status": "updated"}


@router.get("/{checker_id}/configs")
async def get_checker_configs(
    checker_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get configurations for a checker."""
    configs = db.query(CheckerConfig).filter(CheckerConfig.checker_id == checker_id).all()
    
    return [
        {
            "id": str(config.id),
            "checker_id": str(config.checker_id),
            "secret_name": config.secret_name,
            "weight": config.weight,
            "timeout_seconds": config.timeout_seconds,
            "enabled": config.enabled,
        }
        for config in configs
    ]


@router.post("/{checker_id}/configs")
async def create_checker_config(
    checker_id: UUID,
    config_data: CheckerConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Create or update checker configuration (admin only)."""
    # Check if config already exists (by checker_id and secret_name combination)
    existing = db.query(CheckerConfig).filter(
        CheckerConfig.checker_id == checker_id,
        CheckerConfig.secret_name == config_data.secret_name
    ).first()
    
    if existing:
        # Update existing
        existing.weight = config_data.weight
        existing.timeout_seconds = config_data.timeout_seconds
        existing.enabled = config_data.enabled
        existing.updated_at = datetime.utcnow()
    else:
        # Create new
        config = CheckerConfig(
            checker_id=checker_id,
            secret_name=config_data.secret_name,
            weight=config_data.weight,
            timeout_seconds=config_data.timeout_seconds,
            enabled=config_data.enabled,
        )
        db.add(config)
    
    db.commit()
    
    # Invalidate secret cache if secret_name changed
    if config_data.secret_name:
        secret_service.invalidate_cache(config_data.secret_name)
    
    return {"status": "created"}


@router.get("/implementations")
async def get_checker_implementations(
    current_user: User = Depends(get_current_user),
):
    """List all available checker implementations."""
    implementations = checker_registry.list_all()
    
    return [
        {
            "key": key,
            "description": f"Checker implementation: {key}",
            # TODO: Add more metadata from checker class
        }
        for key in implementations.keys()
    ]


@router.get("/secrets")
async def get_secrets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """List all secrets (admin only, values masked)."""
    secrets = db.query(Secret).all()
    
    return [
        {
            "name": secret.name,
            "description": secret.description,
            "created_at": secret.created_at.isoformat(),
            "has_value": bool(secret.value),
        }
        for secret in secrets
    ]


@router.get("/secrets/{secret_name}")
async def get_secret(
    secret_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Get a specific secret (admin only)."""
    secret = db.query(Secret).filter(Secret.name == secret_name).first()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    
    return {
        "name": secret.name,
        "value": secret.value,  # Expose value for admin
        "description": secret.description,
    }


@router.post("/secrets")
async def create_secret(
    secret_data: SecretCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Create or update secret (admin only)."""
    # Update secret service
    await secret_service.set_secret(secret_data.name, secret_data.value)
    
    # Also update DB
    secret = db.query(Secret).filter(Secret.name == secret_data.name).first()
    if secret:
        secret.value = secret_data.value
        if secret_data.description:
            secret.description = secret_data.description
        secret.updated_at = datetime.utcnow()
    else:
        secret = Secret(
            name=secret_data.name,
            value=secret_data.value,
            description=secret_data.description,
        )
        db.add(secret)
    
    db.commit()
    
    return {"status": "created"}


@router.put("/secrets/{secret_name}")
async def update_secret(
    secret_name: str,
    secret_data: SecretCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Update secret (admin only)."""
    secret = db.query(Secret).filter(Secret.name == secret_name).first()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    
    secret.value = secret_data.value
    if secret_data.description:
        secret.description = secret_data.description
    secret.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Update cache
    await secret_service.set_secret(secret_name, secret_data.value)
    
    return {"status": "updated"}


@router.delete("/secrets/{secret_name}")
async def delete_secret(
    secret_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """Delete secret (admin only)."""
    secret = db.query(Secret).filter(Secret.name == secret_name).first()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    
    db.delete(secret)
    db.commit()
    
    # Remove from cache
    await secret_service.delete_secret(secret_name)
    
    return {"status": "deleted"}

