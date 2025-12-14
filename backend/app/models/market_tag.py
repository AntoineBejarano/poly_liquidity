"""
MarketTag model - tabla de relación many-to-many entre Markets y Tags.
"""
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class MarketTag(BaseModel):
    """
    MarketTag model - relación many-to-many entre Markets y Tags.
    
    Un Market puede tener múltiples Tags.
    Un Tag puede aplicarse a múltiples Markets.
    """
    
    __tablename__ = "market_tags"
    
    # Market al que pertenece este tag
    market_id = Column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, index=True)
    
    # Tag asociado
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False, index=True)
    
    # Relationships
    market = relationship("Market", back_populates="tags")
    tag = relationship("Tag", back_populates="markets")
    
    # Unique constraint: un Market no puede tener el mismo Tag dos veces
    __table_args__ = (
        UniqueConstraint('market_id', 'tag_id', name='uq_market_tag'),
    )

