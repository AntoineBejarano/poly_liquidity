"""
User metadata model - extends neon_auth.users_sync with additional information.
"""
from sqlalchemy import Column, String, ForeignKey, DateTime
from datetime import datetime
from app.models.base import Base


class UserMetadata(Base):
    """
    User metadata model for additional information.
    
    The actual user data comes from neon_auth.users_sync (managed by Stack Auth).
    This table only stores additional metadata like roles.
    
    Note: This does NOT extend BaseModel because user_id is the primary key (not id UUID).
    """
    
    __tablename__ = "user_metadata"
    
    # Foreign key to neon_auth.users_sync.id (TEXT)
    user_id = Column(String, ForeignKey('neon_auth.users_sync.id'), primary_key=True, nullable=False)
    role = Column(String, nullable=False, default="viewer")  # admin, viewer
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Note: We don't store email/name here - they come from neon_auth.users_sync
    # We can access them via a relationship or by querying neon_auth.users_sync directly
