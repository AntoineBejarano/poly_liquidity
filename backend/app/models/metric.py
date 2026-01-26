"""
Metric model for persistent storage.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.models.base import Base
from datetime import datetime


class Metric(Base):
    """Modelo de métrica para almacenamiento persistente."""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    metric_name = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    labels = Column(Text)  # JSON string
    component = Column(String(100), index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

