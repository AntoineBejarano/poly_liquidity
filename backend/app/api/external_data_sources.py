"""
External Data Sources API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.api.auth import get_current_user, User
from app.models.external_data_source import ExternalDataSource

router = APIRouter(prefix="/external-data-sources", tags=["external-data-sources"])


class ExternalDataSourceResponse(BaseModel):
    """External data source response model."""
    id: str
    name: str
    source_type: str
    is_active: bool
    config: dict
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("")
async def get_external_data_sources(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ExternalDataSourceResponse]:
    """List all external data sources."""
    query = db.query(ExternalDataSource)
    
    if is_active is not None:
        query = query.filter(ExternalDataSource.is_active == is_active)
    
    sources = query.order_by(ExternalDataSource.created_at.desc()).all()
    
    return [
        ExternalDataSourceResponse(
            id=str(source.id),
            name=source.name,
            source_type=source.source_type,
            is_active=source.is_active,
            config=source.config or {},
            created_at=source.created_at.isoformat() if source.created_at else "",
            updated_at=source.updated_at.isoformat() if source.updated_at else "",
        )
        for source in sources
    ]

