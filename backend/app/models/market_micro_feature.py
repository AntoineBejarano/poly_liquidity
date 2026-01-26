"""
Market Micro Feature model for orderbook features persistence.

Almacena features calculadas del orderbook (depth, impact, spread, etc.)
para análisis histórico y ranking de mercados.
"""
from sqlalchemy import Column, String, Float, BigInteger, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import BaseModel


class MarketMicroFeature(BaseModel):
    """
    Modelo para persistir features del orderbook por asset_id.
    
    Se guarda en batch cada X segundos (configurable) para evitar
    sobrecarga de escritura en DB.
    
    Retención: 30 días (configurable)
    Agregación: Opcional para datos > 7 días (rollups por minuto)
    """
    
    __tablename__ = "market_micro_features"
    
    # Asset ID de Polymarket (token ID)
    asset_id = Column(String, nullable=False, index=True)
    
    # Market ID interno (opcional, para joins)
    market_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Event ID interno (opcional, para joins)
    event_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Timestamp del snapshot (ms)
    ts_ms = Column(BigInteger, nullable=False, index=True)
    
    # BBO (Best Bid/Offer)
    best_bid_price = Column(Float, nullable=True)
    best_bid_size = Column(Float, nullable=True)
    best_ask_price = Column(Float, nullable=True)
    best_ask_size = Column(Float, nullable=True)
    
    # Spread y mid
    spread_bps = Column(Float, nullable=True)
    mid = Column(Float, nullable=True)
    
    # Depth at different bps (BUY side - asks)
    depth_usdc_at_25bps = Column(Float, nullable=True)
    depth_usdc_at_50bps = Column(Float, nullable=True)
    depth_usdc_at_100bps = Column(Float, nullable=True)
    
    # Impact for different USDC sizes (BUY side)
    impact_bps_for_usdc_100 = Column(Float, nullable=True)
    impact_bps_for_usdc_500 = Column(Float, nullable=True)
    impact_bps_for_usdc_1000 = Column(Float, nullable=True)
    impact_bps_for_usdc_5000 = Column(Float, nullable=True)
    
    # Concentration
    concentration_top3_pct = Column(Float, nullable=True)
    
    # Update rate
    update_rate_hz = Column(Float, nullable=True)
    
    # Replenishment score
    replenishment_score = Column(Float, nullable=True)
    
    # Staleness
    staleness_ms = Column(Integer, nullable=True)
    
    # Integrity metadata (JSONB para flexibilidad)
    integrity = Column(JSONB, nullable=True)
    
    # Índices compuestos para queries eficientes
    __table_args__ = (
        Index('idx_micro_features_asset_ts', 'asset_id', 'ts_ms'),
        Index('idx_micro_features_ts', 'ts_ms'),
        Index('idx_micro_features_market_ts', 'market_id', 'ts_ms'),
    )

