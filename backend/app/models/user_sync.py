"""
Model for neon_auth.users_sync table (managed by Stack Auth).
This is a read-only view of the actual users table.
"""
from sqlalchemy import Column, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

# Use the same Base as other models, but UserSync will specify schema in __table_args__
from app.models.base import Base


class UserSync(Base):
    """
    Model for neon_auth.users_sync table.
    
    This table is managed by Stack Auth and is immutable from our application.
    We can only read from it, not write to it.
    
    Note: This uses the same Base as other models but specifies the schema in __table_args__.
    """
    
    __tablename__ = "users_sync"
    __table_args__ = {'schema': 'neon_auth'}
    
    # Override id to use Text instead of UUID (since Stack Auth uses text IDs)
    id = Column(Text, primary_key=True)
    name = Column(Text)
    email = Column(Text)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))
    # Use JSON for SQLite compatibility, JSONB for PostgreSQL
    raw_json = Column(JSON, nullable=False)
    
    # Note: We don't inherit created_at/updated_at from BaseModel because
    # this table uses different column types and is managed by Stack Auth

