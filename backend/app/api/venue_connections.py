"""
Venue Connections API endpoints.

Endpoints para gestionar conexiones con venues externos (Pinnacle, Bet365, etc.).
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.api.auth import get_current_user, User
from app.models.external_data_source import ExternalDataSource

router = APIRouter(prefix="/venue-connections", tags=["venue-connections"])


class VenueConnectionResponse(BaseModel):
    """Venue connection response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    venue_name: str
    venue_type: str
    is_active: bool
    is_connected: bool
    last_connection_check: Optional[str]
    config: dict


@router.get("")
async def get_venue_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[VenueConnectionResponse]:
    """
    Lista todas las conexiones con venues externos.
    
    Por ahora, retorna las external data sources que son de tipo "venue".
    """
    # Buscar external data sources que sean venues
    venues = db.query(ExternalDataSource).filter(
        ExternalDataSource.source_type.in_(["pinnacle", "bet365", "venue"])
    ).all()
    
    return [
        VenueConnectionResponse(
            id=str(venue.id),
            venue_name=venue.name,
            venue_type=venue.source_type,
            is_active=venue.is_active,
            is_connected=venue.is_active,  # Por ahora, asumimos que si está activo está conectado
            last_connection_check=None,  # TODO: Implementar tracking de última conexión
            config=venue.config or {},
        )
        for venue in venues
    ]

