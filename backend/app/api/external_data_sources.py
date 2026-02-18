"""
External Data Sources API endpoints.

CRUD por usuario: listado filtrado por created_by; crear con created_by = current_user.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app.api.auth import get_current_user, User
from app.models.external_data_source import ExternalDataSource

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

