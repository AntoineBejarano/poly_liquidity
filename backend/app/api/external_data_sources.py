"""
External Data Sources API endpoints.

CRUD por usuario: listado filtrado por created_by; crear con created_by = current_user.
Para PS3838: verifica credenciales antes de guardar.
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app.api.auth import get_current_user, User
from app.models.external_data_source import ExternalDataSource
from app.core.ps3838.client import PS3838Client, PS3838ClientError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external-data-sources", tags=["external-data-sources"])


class ExternalDataSourceResponse(BaseModel):
    """External data source response model."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    connector_type: str
    is_active: bool
    config: dict
    created_at: str
    updated_at: str


class ExternalDataSourceCreate(BaseModel):
    """Request body for creating an external data source."""
    name: str = Field(..., min_length=1, max_length=255)
    connector_type: str = Field(..., min_length=1)  # e.g. ps3838, telegram, custom_api, pinnacle
    description: Optional[str] = None
    connector_config: Dict[str, Any] = Field(default_factory=dict)


class ExternalDataSourceUpdate(BaseModel):
    """Request body for updating an external data source (partial)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    connector_config: Optional[Dict[str, Any]] = None


@router.get("")
async def get_external_data_sources(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    connector_type: Optional[str] = Query(None, description="Filter by connector type (e.g. ps3838, telegram)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ExternalDataSourceResponse]:
    """List external data sources of the current user, optionally filtered."""
    query = db.query(ExternalDataSource).filter(ExternalDataSource.created_by == current_user.id)

    if is_active is not None:
        query = query.filter(ExternalDataSource.is_active == is_active)
    if connector_type is not None:
        query = query.filter(ExternalDataSource.connector_type == connector_type)

    sources = query.order_by(ExternalDataSource.created_at.desc()).all()

    return [
        ExternalDataSourceResponse(
            id=str(source.id),
            name=source.name,
            connector_type=source.connector_type,
            is_active=source.is_active,
            config=source.connector_config or {},
            created_at=source.created_at.isoformat() if source.created_at else "",
            updated_at=source.updated_at.isoformat() if source.updated_at else "",
        )
        for source in sources
    ]


@router.post("")
async def create_external_data_source(
    body: ExternalDataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExternalDataSourceResponse:
    """Create an external data source for the current user."""
    if body.connector_type == "ps3838":
        config = body.connector_config or {}
        username = config.get("username") or ""
        password = config.get("password") or ""
        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario y contraseña API son obligatorios para PS3838.",
            )
        try:
            client = PS3838Client(username=username, password=password)
            await client.verify_credentials()
        except PS3838ClientError as e:
            logger.warning("PS3838 verify failed for user %s: %s", current_user.id, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        except Exception as e:
            logger.warning("PS3838 verify error for user %s: %s", current_user.id, e)
            err_msg = str(e)
            if "401" in err_msg or "Unauthorized" in err_msg:
                detail = "Usuario o contraseña API incorrectos. Revisa las credenciales en tu cuenta."
            elif "403" in err_msg or "Forbidden" in err_msg:
                detail = "Acceso denegado. Verifica que tu cuenta tenga acceso a la API."
            elif "timeout" in err_msg.lower() or "Connection" in err_msg:
                detail = "No se pudo conectar con PS3838. Verifica tu conexión a internet."
            else:
                detail = f"No se pudo verificar la conexión con PS3838. Revisa usuario, contraseña y que tu cuenta tenga acceso a la API. Error: {err_msg}"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            ) from e

    source = ExternalDataSource(
        name=body.name,
        connector_type=body.connector_type,
        description=body.description,
        connector_config=body.connector_config or {},
        is_active=True,
        created_by=current_user.id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return ExternalDataSourceResponse(
        id=str(source.id),
        name=source.name,
        connector_type=source.connector_type,
        is_active=source.is_active,
        config=source.connector_config or {},
        created_at=source.created_at.isoformat() if source.created_at else "",
        updated_at=source.updated_at.isoformat() if source.updated_at else "",
    )


@router.patch("/{source_id}")
async def update_external_data_source(
    source_id: str,
    body: ExternalDataSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExternalDataSourceResponse:
    """Update an external data source (name, connector_config). Only owner can update."""
    from uuid import UUID
    try:
        uid = UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    source = db.query(ExternalDataSource).filter(
        ExternalDataSource.id == uid,
        ExternalDataSource.created_by == current_user.id,
    ).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    if body.name is not None:
        source.name = body.name
    if body.connector_config is not None:
        current = source.connector_config or {}
        incoming = body.connector_config
        merged = dict(current)
        for k, v in incoming.items():
            if v is None:
                merged.pop(k, None)
            elif isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**(merged[k] or {}), **v}
            else:
                merged[k] = v
        source.connector_config = merged
    db.commit()
    db.refresh(source)
    return ExternalDataSourceResponse(
        id=str(source.id),
        name=source.name,
        connector_type=source.connector_type,
        is_active=source.is_active,
        config=source.connector_config or {},
        created_at=source.created_at.isoformat() if source.created_at else "",
        updated_at=source.updated_at.isoformat() if source.updated_at else "",
    )
