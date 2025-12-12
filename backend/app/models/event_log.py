"""
Event Log model for Historical Replay.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.dialects.sqlite import JSON
from app.models.base import Base
from datetime import datetime


class EventLog(Base):
    """Event log entry for historical replay."""
    
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(100), nullable=False, index=True)  # event type
    timestamp = Column(DateTime, nullable=False, index=True)
    trace_id = Column(String(36), index=True)  # UUID string
    event_data = Column(JSON, nullable=False)  # Full event payload
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_type_timestamp', 'type', 'timestamp'),
        Index('idx_trace_id_timestamp', 'trace_id', 'timestamp'),
    )

